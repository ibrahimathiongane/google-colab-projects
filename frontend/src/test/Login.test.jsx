import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "../i18n";
import Login from "../pages/Login";

vi.mock("../api", () => ({
  api: {
    login: vi.fn(),
    register: vi.fn(),
  },
  localDate: () => "2026-09-30",
}));

const { api } = await import("../api");

describe("Login", () => {
  it("logs in and hands the tokens to the parent", async () => {
    api.login.mockResolvedValue({
      token: "t1",
      refresh_token: "r1",
      user: { id: 1, email: "alice@example.com", name: "Alice" },
    });
    const onLogin = vi.fn();
    const user = userEvent.setup();
    render(<Login onLogin={onLogin} />);

    await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => expect(onLogin).toHaveBeenCalledTimes(1));
    expect(api.login).toHaveBeenCalledWith("alice@example.com", "secret-pass");
    expect(onLogin).toHaveBeenCalledWith(
      { id: 1, email: "alice@example.com", name: "Alice" },
      { token: "t1", refresh_token: "r1" },
    );
  });

  it("sends the name when registering", async () => {
    api.register.mockResolvedValue({
      token: "t2",
      refresh_token: "r2",
      user: { id: 2, name: "Bob" },
    });
    const onLogin = vi.fn();
    const user = userEvent.setup();
    render(<Login onLogin={onLogin} />);

    await user.click(screen.getByRole("button", { name: "Need an account? Register" }));
    await user.type(screen.getByPlaceholderText("Name"), "Bob");
    await user.type(screen.getByPlaceholderText("Email"), "bob@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(api.register).toHaveBeenCalledWith(
      "bob@example.com",
      "secret-pass",
      "Bob",
    ));
    expect(onLogin).toHaveBeenCalled();
  });

  it("shows the translated API error instead of failing silently", async () => {
    api.login.mockRejectedValue(new Error("Invalid credentials"));
    const user = userEvent.setup();
    render(<Login onLogin={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "wrong-pass");
    await user.click(screen.getByRole("button", { name: "Login" }));

    // Raw backend message → localized string.
    expect(
      await screen.findByText("Incorrect email or password."),
    ).toBeInTheDocument();
  });
});

describe("Login in French", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders every label in French and translates backend errors", async () => {
    api.login.mockRejectedValue(new Error("Invalid credentials"));
    await i18n.changeLanguage("fr");
    const user = userEvent.setup();
    render(<Login onLogin={vi.fn()} />);

    expect(screen.getByPlaceholderText("Courriel")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Mot de passe")).toBeInTheDocument();
    expect(screen.getByText(/méthode scientifique/)).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("Courriel"), "a@b.co");
    await user.type(screen.getByPlaceholderText("Mot de passe"), "nope");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(
      await screen.findByText("Courriel ou mot de passe incorrect."),
    ).toBeInTheDocument();
  });
});
