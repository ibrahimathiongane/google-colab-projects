import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Plan from "../pages/Plan";

vi.mock("../api", () => ({
  api: {
    billingStatus: vi.fn(),
    checkout: vi.fn(),
    portal: vi.fn(),
  },
}));

const { api } = await import("../api");

// jsdom cannot navigate — capture where the page would have gone.
const locationMock = { href: "" };
beforeAll(() => {
  Object.defineProperty(window, "location", {
    value: locationMock,
    writable: true,
    configurable: true,
  });
});

const FREE_STATUS = {
  plan: "free",
  subscription_status: null,
  current_period_end: null,
  cancel_at_period_end: false,
  has_customer: false,
};

function renderAt(path = "/plan") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Plan />
    </MemoryRouter>,
  );
}

/** The label is split across text nodes ("Current plan: " + <strong>). */
async function expectCurrentPlan(name) {
  // The badge says "Current plan" too — the colon only appears in the label.
  const tagline = await screen.findByText(/Current plan:/);
  expect(tagline.querySelector("strong")).toHaveTextContent(name);
}

describe("Plan", () => {
  afterEach(() => {
    vi.clearAllMocks();
    locationMock.href = "";
  });

  it("shows the free plan as current by default", async () => {
    api.billingStatus.mockResolvedValue(FREE_STATUS);
    renderAt();

    await expectCurrentPlan("Free");
    expect(screen.getByRole("button", { name: "Go Pro" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Buy lifetime" }),
    ).toBeInTheDocument();
    // No billing account yet → no management link.
    expect(screen.queryByRole("button", { name: "Manage billing" })).toBeNull();
  });

  it("starts a Stripe checkout and redirects to the hosted page", async () => {
    api.billingStatus.mockResolvedValue(FREE_STATUS);
    api.checkout.mockResolvedValue({ url: "https://checkout.stripe.com/x" });
    const user = userEvent.setup();
    renderAt();

    await user.click(await screen.findByRole("button", { name: "Go Pro" }));
    await waitFor(() => expect(api.checkout).toHaveBeenCalledWith("pro"));
    expect(locationMock.href).toBe("https://checkout.stripe.com/x");
  });

  it("offers the billing portal once a customer exists", async () => {
    api.billingStatus.mockResolvedValue({
      ...FREE_STATUS,
      plan: "pro",
      subscription_status: "active",
      has_customer: true,
    });
    api.portal.mockResolvedValue({ url: "https://billing.stripe.com/x" });
    const user = userEvent.setup();
    renderAt();

    await expectCurrentPlan("Pro");
    // The current plan is highlighted instead of a second purchase button.
    expect(screen.queryByRole("button", { name: "Go Pro" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Manage billing" }));
    await waitFor(() => expect(api.portal).toHaveBeenCalled());
    expect(locationMock.href).toBe("https://billing.stripe.com/x");
  });

  it("confirms a completed checkout from the redirect query", async () => {
    api.billingStatus.mockResolvedValue({
      ...FREE_STATUS,
      plan: "pro",
      subscription_status: "active",
      has_customer: true,
    });
    renderAt("/plan?checkout=success");
    expect(
      await screen.findByText("Payment confirmed — thank you!"),
    ).toBeInTheDocument();
  });

  it("translates a billing failure", async () => {
    api.billingStatus.mockResolvedValue(FREE_STATUS);
    api.checkout.mockRejectedValue(new Error("Billing is not configured"));
    const user = userEvent.setup();
    renderAt();

    // Unknown backend message → passes through untranslated (by design).
    await user.click(await screen.findByRole("button", { name: "Buy lifetime" }));
    expect(await screen.findByText("Billing is not configured")).toBeInTheDocument();
  });
});
