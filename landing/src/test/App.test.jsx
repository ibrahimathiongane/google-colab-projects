import { afterEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
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
    expect(screen.queryAllByText("Bientôt")).toHaveLength(0);
    const pricing = within(document.getElementById("pricing"));
    expect(pricing.getByRole("link", { name: "Passer Pro" })).toHaveAttribute(
      "href",
      `${APP_URL}/plan`,
    );
  });

  it("links every plan to the right place in the app", async () => {
    await i18n.changeLanguage("en");
    render(<App />);
    const pricing = within(document.getElementById("pricing"));
    expect(screen.queryAllByText("Coming soon")).toHaveLength(0);
    // The hero shares the "Start free" copy — scope to the pricing cards.
    expect(pricing.getByRole("link", { name: "Start free" })).toHaveAttribute(
      "href",
      `${APP_URL}/login`,
    );
    expect(pricing.getByRole("link", { name: "Get Pro" })).toHaveAttribute(
      "href",
      `${APP_URL}/plan`,
    );
    expect(pricing.getByRole("link", { name: "Get Lifetime" })).toHaveAttribute(
      "href",
      `${APP_URL}/plan`,
    );
  });
});
