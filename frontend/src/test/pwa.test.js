import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { registerServiceWorker } from "../pwa";

const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(here, "..", "..", "public");

function readPublic(name) {
  return fs.readFileSync(path.join(publicDir, name), "utf8");
}

describe("registerServiceWorker", () => {
  it("does not register outside production", async () => {
    const serviceWorker = { register: vi.fn() };
    const result = await registerServiceWorker({
      prod: false,
      serviceWorker,
    });
    expect(result).toBeNull();
    expect(serviceWorker.register).not.toHaveBeenCalled();
  });

  it("does nothing without SW support", async () => {
    const result = await registerServiceWorker({
      prod: true,
      serviceWorker: undefined,
    });
    expect(result).toBeNull();
  });

  it("registers /sw.js in production", async () => {
    const serviceWorker = { register: vi.fn().mockResolvedValue({}) };
    await registerServiceWorker({ prod: true, serviceWorker });
    expect(serviceWorker.register).toHaveBeenCalledWith("/sw.js");
  });

  it("swallows registration failures", async () => {
    const serviceWorker = {
      register: vi.fn().mockRejectedValue(new Error("insecure")),
    };
    await expect(
      registerServiceWorker({ prod: true, serviceWorker }),
    ).resolves.toBeNull();
  });
});

describe("manifest.json", () => {
  const manifest = JSON.parse(readPublic("manifest.json"));

  it("declares the fields installability requires", () => {
    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.start_url).toBe("/");
    expect(manifest.scope).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i);
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("ships 192, 512 and maskable icons that exist on disk", () => {
    const sizes = manifest.icons.map((i) => i.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");
    expect(manifest.icons.some((i) => i.purpose === "maskable")).toBe(true);

    for (const icon of manifest.icons) {
      if (icon.type === "image/svg+xml") continue;
      expect(fs.existsSync(path.join(publicDir, path.basename(icon.src)))).toBe(
        true,
      );
    }
  });
});

describe("index.html PWA wiring", () => {
  const html = fs.readFileSync(
    path.join(here, "..", "..", "index.html"),
    "utf8",
  );

  it("links the manifest, the icons and the theme color", () => {
    expect(html).toContain('rel="manifest" href="/manifest.json"');
    expect(html).toContain('rel="apple-touch-icon" href="/apple-touch-icon.png"');
    expect(html).toContain('name="theme-color" content="#4caf50"');
    expect(html).toContain('name="viewport"');
  });
});

describe("service worker fetch policy", () => {
  const handlers = {};
  let cachesMock;
  let fetchMock;

  beforeEach(async () => {
    handlers.clear?.();
    vi.resetModules();
    cachesMock = {
      match: vi.fn().mockResolvedValue(null),
      open: vi.fn().mockResolvedValue({ addAll: vi.fn(), put: vi.fn() }),
      keys: vi.fn().mockResolvedValue([]),
      delete: vi.fn().mockResolvedValue(true),
    };
    fetchMock = vi.fn();
    vi.stubGlobal("caches", cachesMock);
    vi.stubGlobal("fetch", fetchMock);

    vi.spyOn(self, "addEventListener").mockImplementation((type, fn) => {
      handlers[type] = fn;
    });
    await import("../../public/sw.js");
  });

  function fakeEvent(request) {
    return { request, respondWith: vi.fn() };
  }

  it("never intercepts API calls (freshness + privacy)", () => {
    const event = fakeEvent({
      method: "GET",
      url: "http://localhost/api/habits/",
      mode: "cors",
    });
    handlers.fetch(event);
    expect(event.respondWith).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("falls back to the app shell when navigation is offline", async () => {
    const shell = { ok: true, body: "<html>…" };
    cachesMock.match.mockResolvedValueOnce(null).mockResolvedValueOnce(shell);
    fetchMock.mockRejectedValue(new Error("offline"));

    const event = fakeEvent({
      method: "GET",
      url: "http://localhost/insights",
      mode: "navigate",
    });
    handlers.fetch(event);
    expect(event.respondWith).toHaveBeenCalledTimes(1);

    const response = await event.respondWith.mock.calls[0][0];
    expect(response).toBe(shell);
  });

  it("serves cached hashed assets without hitting the network", async () => {
    const cached = { ok: true, body: "js-bundle" };
    cachesMock.match.mockResolvedValueOnce(cached);

    const event = fakeEvent({
      method: "GET",
      url: "http://localhost/assets/index-abc123.js",
      mode: "cors",
    });
    handlers.fetch(event);

    const response = await event.respondWith.mock.calls[0][0];
    expect(response).toBe(cached);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("skips non-GET requests", () => {
    const event = fakeEvent({
      method: "POST",
      url: "http://localhost/api/tracking/checkin",
      mode: "cors",
    });
    handlers.fetch(event);
    expect(event.respondWith).not.toHaveBeenCalled();
  });
});
