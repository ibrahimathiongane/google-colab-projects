import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "OK",
    json: async () => body,
  };
}

describe("localDate", () => {
  it("uses the local calendar day, not UTC", async () => {
    const { localDate } = await import("../api");
    // 1st Jan local time — UTC would already be a different year in some TZs.
    expect(localDate(new Date(2026, 0, 5, 0, 30))).toBe("2026-01-05");
    expect(localDate(new Date(2026, 11, 31, 23, 59))).toBe("2026-12-31");
  });
});

describe("request helper", () => {
  it("returns the parsed payload on success", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, [{ id: 1 }]));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await expect(api.listHabits()).resolves.toEqual([{ id: 1 }]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/habits/",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("refreshes an expired access token once and retries", async () => {
    const { api, setTokens } = await import("../api");
    setTokens({ token: "expired", refresh_token: "refresh-1" });

    const fetchMock = vi
      .fn()
      // 1. the original call sees an expired token
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Authentication required" }))
      // 2. the refresh call succeeds
      .mockResolvedValueOnce(
        jsonResponse(200, { token: "fresh", refresh_token: "refresh-2" }),
      )
      // 3. the retried call succeeds with the new token
      .mockResolvedValueOnce(jsonResponse(200, { id: 7 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.me()).resolves.toEqual({ id: 7 });
    expect(fetchMock).toHaveBeenCalledTimes(3);

    const refreshBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(refreshBody.refresh_token).toBe("refresh-1");

    const retryHeaders = fetchMock.mock.calls[2][1].headers;
    expect(retryHeaders.Authorization).toBe("Bearer fresh");
  });

  it("drops the tokens when the refresh itself fails", async () => {
    const { api, setTokens } = await import("../api");
    setTokens({ token: "expired", refresh_token: "refresh-1" });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: "nope" }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: "invalid" }));
    vi.stubGlobal("fetch", fetchMock);

    // The original 401 is surfaced (not the refresh endpoint's error),
    // and the dead tokens are dropped so we do not loop forever.
    await expect(api.me()).rejects.toThrow("nope");
    expect(fetchMock).toHaveBeenCalledTimes(2); // no blind retry
    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("surfaces FastAPI validation errors as a readable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          detail: [{ loc: ["body", "password"], msg: "String too short" }],
        }),
      ),
    );

    const { api } = await import("../api");
    await expect(
      api.register("a@b.co", "x", "n"),
    ).rejects.toThrow("password: String too short");
  });
});

describe("password reset endpoints", () => {
  it("forgotPassword posts the email to the public endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await expect(api.forgotPassword("a@b.co")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/users/forgot-password",
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      email: "a@b.co",
    });
  });

  it("resetPassword posts the token with the new password", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await api.resetPassword("raw-token", "brand-new-pass");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/users/reset-password",
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      token: "raw-token",
      password: "brand-new-pass",
    });
  });
});

describe("billing endpoints", () => {
  it("billingStatus reads the current plan", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, { plan: "free", has_customer: false }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await expect(api.billingStatus()).resolves.toEqual({
      plan: "free",
      has_customer: false,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/billing/",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("checkout posts the chosen plan", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { url: "https://stripe/x" }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await expect(api.checkout("lifetime")).resolves.toEqual({
      url: "https://stripe/x",
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      plan: "lifetime",
    });
  });

  it("portal opens the Stripe customer portal", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { url: "https://portal/x" }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("../api");
    await api.portal();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/billing/portal",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
