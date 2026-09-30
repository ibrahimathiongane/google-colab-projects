import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ResetPassword from "../pages/ResetPassword";

vi.mock("../api", () => ({
  api: {
    resetPassword: vi.fn(),
  },
}));

const { api } = await import("../api");

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ResetPassword />
    </MemoryRouter>,
  );
}

describe("ResetPassword", () => {
  it("asks for a new link when the token is missing", () => {
    renderAt("/reset-password");
    expect(screen.getByText(/This reset link is invalid/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Request a new link" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });

  it("rejects mismatched passwords without calling the API", async () => {
    const user = userEvent.setup();
    renderAt("/reset-password?token=abc123token");

    await user.type(screen.getByPlaceholderText("New password"), "first-pass");
    await user.type(screen.getByPlaceholderText("Confirm new password"), "other-pass");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(await screen.findByText("Passwords don't match.")).toBeInTheDocument();
    expect(api.resetPassword).not.toHaveBeenCalled();
  });

  it("submits the token with the new password and confirms", async () => {
    api.resetPassword.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderAt("/reset-password?token=abc123token");

    await user.type(screen.getByPlaceholderText("New password"), "brand-new-pass");
    await user.type(screen.getByPlaceholderText("Confirm new password"), "brand-new-pass");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() =>
      expect(api.resetPassword).toHaveBeenCalledWith(
        "abc123token",
        "brand-new-pass",
      ),
    );
    expect(screen.getByText(/Password updated/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Login" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("surfaces an invalid link as a translated error", async () => {
    api.resetPassword.mockRejectedValue(new Error("Invalid or expired reset link"));
    const user = userEvent.setup();
    renderAt("/reset-password?token=expiredtoken");

    await user.type(screen.getByPlaceholderText("New password"), "brand-new-pass");
    await user.type(screen.getByPlaceholderText("Confirm new password"), "brand-new-pass");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(
      await screen.findByText(
        "This reset link is invalid or has expired. Request a new one.",
      ),
    ).toBeInTheDocument();
  });
});
