import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RemindersToggle from "../components/RemindersToggle";

vi.mock("../api", () => ({
  api: {
    remindersStatus: vi.fn(),
    remindersPublicKey: vi.fn(),
    remindersSubscribe: vi.fn(),
    remindersUnsubscribe: vi.fn(),
  },
  tzOffset: () => 120, // fixed offset keeps the payload assertion exact
}));

const { api } = await import("../api");

function fakeSubscription() {
  return {
    endpoint: "https://push.example.com/ep-1",
    toJSON: () => ({ keys: { p256dh: "p256dh", auth: "auth" } }),
    unsubscribe: vi.fn().mockResolvedValue(true),
  };
}

function stubBrowser({ permission, registration, requestPermission }) {
  vi.stubGlobal("Notification", {
    permission,
    // With permission "default" the prompt is pending — unless the test
    // injects its own answer, assume the user accepts it.
    requestPermission:
      requestPermission ||
      vi.fn().mockResolvedValue(permission === "default" ? "granted" : permission),
  });
  vi.stubGlobal("PushManager", class PushManager {});
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { getRegistration: vi.fn().mockResolvedValue(registration) },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete navigator.serviceWorker;
  vi.clearAllMocks();
});

describe("RemindersToggle", () => {
  it("is disabled when push notifications are unsupported", async () => {
    render(<RemindersToggle />);
    const button = await screen.findByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute(
      "title",
      "Reminders need a browser with push notification support",
    );
    expect(api.remindersStatus).not.toHaveBeenCalled();
  });

  it("stays unsupported inside the native Capacitor shell", async () => {
    // WebView push never delivers — even with a fully capable browser API.
    stubBrowser({ permission: "default", registration: null });
    window.Capacitor = { isNativePlatform: () => true };
    try {
      render(<RemindersToggle />);
      const button = await screen.findByRole("button");
      expect(button).toBeDisabled();
      expect(api.remindersStatus).not.toHaveBeenCalled();
    } finally {
      delete window.Capacitor;
    }
  });

  it("enables reminders: permission → subscribe → POST", async () => {
    api.remindersStatus.mockResolvedValue({ subscribed: false });
    api.remindersPublicKey.mockResolvedValue({ publicKey: "AQID" });
    api.remindersSubscribe.mockResolvedValue({ subscribed: true });
    const subscription = fakeSubscription();
    const pushManager = {
      getSubscription: vi.fn().mockResolvedValue(null),
      subscribe: vi.fn().mockResolvedValue(subscription),
    };
    stubBrowser({ permission: "default", registration: { pushManager } });
    const user = userEvent.setup();
    render(<RemindersToggle />);

    const button = await screen.findByRole("button", {
      name: "Enable reminders",
    });
    await user.click(button);

    await waitFor(() =>
      expect(api.remindersSubscribe).toHaveBeenCalledTimes(1),
    );
    expect(pushManager.subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: expect.any(Uint8Array),
    });
    expect(api.remindersSubscribe).toHaveBeenCalledWith({
      endpoint: "https://push.example.com/ep-1",
      keys: { p256dh: "p256dh", auth: "auth" },
      tz_offset: 120,
      lang: "en",
    });
    expect(
      await screen.findByRole("button", { name: "Disable reminders" }),
    ).toBeEnabled();
  });

  it("disables reminders: unsubscribe from the server and the browser", async () => {
    api.remindersStatus.mockResolvedValue({ subscribed: true });
    api.remindersUnsubscribe.mockResolvedValue({ subscribed: false });
    const subscription = fakeSubscription();
    const pushManager = {
      getSubscription: vi.fn().mockResolvedValue(subscription),
      subscribe: vi.fn(),
    };
    stubBrowser({ permission: "granted", registration: { pushManager } });
    const user = userEvent.setup();
    render(<RemindersToggle />);

    const button = await screen.findByRole("button", {
      name: "Disable reminders",
    });
    await user.click(button);

    await waitFor(() =>
      expect(api.remindersUnsubscribe).toHaveBeenCalledWith(
        "https://push.example.com/ep-1",
      ),
    );
    expect(subscription.unsubscribe).toHaveBeenCalled();
    expect(
      await screen.findByRole("button", { name: "Enable reminders" }),
    ).toBeInTheDocument();
  });

  it("shows the denied hint without prompting when permission was blocked", async () => {
    stubBrowser({ permission: "denied", registration: null });
    render(<RemindersToggle />);

    const button = await screen.findByRole("button", {
      name: "Notifications are blocked in your browser settings",
    });
    expect(button).toBeDisabled();
    expect(api.remindersStatus).not.toHaveBeenCalled();
  });

  it("stays off when the user dismisses the permission prompt", async () => {
    api.remindersStatus.mockResolvedValue({ subscribed: false });
    stubBrowser({
      permission: "default",
      registration: null,
      requestPermission: vi.fn().mockResolvedValue("denied"),
    });
    const user = userEvent.setup();
    render(<RemindersToggle />);

    await user.click(
      await screen.findByRole("button", { name: "Enable reminders" }),
    );
    expect(
      await screen.findByRole("button", {
        name: "Notifications are blocked in your browser settings",
      }),
    ).toBeDisabled();
    expect(api.remindersSubscribe).not.toHaveBeenCalled();
  });

  it("surfaces an unconfigured server as a translated error", async () => {
    api.remindersStatus.mockResolvedValue({ subscribed: false });
    api.remindersPublicKey.mockRejectedValue(
      new Error("Notifications are not configured"),
    );
    const subscription = fakeSubscription();
    const pushManager = {
      getSubscription: vi.fn().mockResolvedValue(null),
      subscribe: vi.fn().mockResolvedValue(subscription),
    };
    stubBrowser({
      permission: "default",
      registration: { pushManager },
      requestPermission: vi.fn().mockResolvedValue("granted"),
    });
    const user = userEvent.setup();
    render(<RemindersToggle />);

    await user.click(
      await screen.findByRole("button", { name: "Enable reminders" }),
    );
    expect(
      await screen.findByText(
        "Push reminders aren't configured on the server yet",
      ),
    ).toBeInTheDocument();
  });
});
