import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App, { APP_URL } from "../App";
import i18n from "../i18n";

afterEach(async () => {
  await i18n.changeLanguage("en");
  localStorage.removeItem("lang");
});

describe("landing page", () => {
  it("renders the hero and points CTAs at the app", async () => {
    await i18n.changeLanguage("en");
    render(<App />);
    expect(
      screen.getByRole("heading", { level: 1, name: /science-based way/ }),
    ).toBeInTheDocument();
    // Hero + Free plan CTAs both go to the login page of the separate frontend.
    const startLinks = screen.getAllByRole("link", { name: "Start free" });
    expect(startLinks.length).toBeGreaterThanOrEqual(1);
    for (const link of startLinks) {
      expect(link).toHaveAttribute("href", `${APP_URL}/login`);
    }
    // Screenshots are the imagery.
    expect(screen.getAllByRole("img")).toHaveLength(2);
  });

  it("renders the full French copy", async () => {
    await i18n.changeLanguage("fr");
    render(<App />);
    expect(
      screen.getByRole("heading", { level: 1, name: /habitudes qui tiennent/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tarifs" })).toHaveAttribute(
      "href",
      "#pricing",
    );
    expect(screen.getAllByText("Bientôt")).toHaveLength(2);
  });

  it("shows paid plans as coming soon, not fake buttons", async () => {
    await i18n.changeLanguage("en");
    render(<App />);
    expect(screen.getAllByText("Coming soon")).toHaveLength(2);
    expect(screen.queryAllByRole("link", { name: "Coming soon" })).toHaveLength(
      0,
    );
  });
});
