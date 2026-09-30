import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { absolutiseHtml, robotsTxt, sitemapXml } from "../../scripts/seo-plugin.js";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("landing SEO head", () => {
  const html = fs.readFileSync(path.join(here, "..", "..", "index.html"), "utf8");

  it("declares Open Graph and Twitter previews", () => {
    for (const needle of [
      'property="og:title"',
      'property="og:description"',
      'property="og:type"',
      'property="og:url"',
      'property="og:image"',
      'name="twitter:card" content="summary_large_image"',
      'name="twitter:image"',
      'name="description"',
    ]) {
      expect(html).toContain(needle);
    }
  });

  it("keeps the landing indexable and defers the site URL to build time", () => {
    expect(html).not.toContain("noindex");
    // Replaced with the absolute URL by the seo-artifacts plugin.
    expect(html).toContain("content=\"__SITE_URL__/images/og.png\"");
  });
});

describe("seo-artifacts plugin", () => {
  it("absolutises the site URL and injects the canonical link", () => {
    const source =
      '<head><meta content="__SITE_URL__/images/og.png" /></head><body/>';
    const out = absolutiseHtml(source, "https://example.com");
    expect(out).toContain('content="https://example.com/images/og.png"');
    expect(out).toContain('<link rel="canonical" href="https://example.com/" />');
    // Idempotent: never injected twice.
    expect(absolutiseHtml(out, "https://example.com")).toBe(out);
  });

  it("writes an absolute Sitemap line in robots.txt", () => {
    expect(robotsTxt("https://example.com")).toContain(
      "Sitemap: https://example.com/sitemap.xml",
    );
  });

  it("emits a one-URL sitemap for the single-page landing", () => {
    const xml = sitemapXml("https://example.com", "2026-09-30");
    expect(xml).toContain("<loc>https://example.com/</loc>");
    expect(xml).toContain("<lastmod>2026-09-30</lastmod>");
  });
});
