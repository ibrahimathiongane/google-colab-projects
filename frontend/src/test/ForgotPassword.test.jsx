import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ForgotPassword from "../pages/ForgotPassword";

vi.mock("../api", () => ({
  api: {
    forgotPassword: vi.fn(),
  },
}));

const { api } = await import("../api");

describe("ForgotPassword", () => {
  it("submits the email and shows the neutral success message", async () => {
    api.forgotPassword.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() =>
      expect(api.forgotPassword).toHaveBeenCalledWith("alice@example.com"),
    );
    // The message must not confirm whether the account exists.
    expect(screen.getByText(/If an account exists/)).toBeInTheDocument();
    expect(screen.queryByRole("form")).toBeNull();
  });

  it("shows a translated backend error", async () => {
    api.forgotPassword.mockRejectedValue(new Error("Too many attempts"));
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.type(screen.getByPlaceholderText("Email"), "a@b.co");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(
      await screen.findByText("Too many attempts. Try again in a few minutes."),
    ).toBeInTheDocument();
  });
});
