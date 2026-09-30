import { afterEach, describe, expect, it } from "vitest";
import i18n from "../i18n";
import { translateApiError } from "../i18n/apiErrors";

afterEach(async () => {
  await i18n.changeLanguage("en");
  localStorage.removeItem("lang");
});

describe("dictionaries", () => {
  it("defaults to English with full coverage of both locales", async () => {
    await i18n.changeLanguage("en");
    expect(i18n.t("login.login")).toBe("Login");

    await i18n.changeLanguage("fr");
    expect(i18n.t("login.login")).toBe("Se connecter");

    // Every key present in EN must exist in FR (and vice versa).
    const flatten = (obj, prefix = "") =>
      Object.entries(obj).flatMap(([k, v]) =>
        typeof v === "object"
          ? flatten(v, `${prefix}${k}.`)
          : [`${prefix}${k}`],
      );
    const enKeys = flatten(i18n.getResource("en", "translation")).sort();
    const frKeys = flatten(i18n.getResource("fr", "translation")).sort();
    expect(frKeys).toEqual(enKeys);
    expect(enKeys.length).toBeGreaterThan(40);
  });

  it("persists the choice and updates <html lang>", async () => {
    await i18n.changeLanguage("fr");
    expect(localStorage.getItem("lang")).toBe("fr");
    expect(document.documentElement.lang).toBe("fr");
    expect(document.title).toBe(i18n.t("app.title"));
  });

  it("pluralizes in both languages", async () => {
    await i18n.changeLanguage("en");
    expect(i18n.t("habit.streak", { count: 1 })).toBe("1 day streak");
    expect(i18n.t("habit.streak", { count: 4 })).toBe("4 day streak");

    await i18n.changeLanguage("fr");
    expect(i18n.t("habit.streak", { count: 1 })).toBe("1 jour de série");
    expect(i18n.t("habit.streak", { count: 4 })).toBe("4 jours de série");
  });

  it("interpolates variables", async () => {
    await i18n.changeLanguage("fr");
    expect(i18n.t("habit.deleteConfirm", { name: "Boire de l'eau" })).toContain(
      "Boire de l'eau",
    );
  });

  it("returns the key for a missing translation instead of crashing", () => {
    expect(i18n.t("does.not.exist")).toBe("does.not.exist");
  });
});

describe("translateApiError", () => {
  it("translates the known backend messages", async () => {
    await i18n.changeLanguage("fr");
    expect(translateApiError(i18n.t.bind(i18n), "Invalid credentials")).toBe(
      "Courriel ou mot de passe incorrect.",
    );
    expect(
      translateApiError(i18n.t.bind(i18n), "Too many attempts, try again later"),
    ).toContain("Trop de tentatives");
  });

  it("passes unknown messages through untouched", () => {
    const t = i18n.t.bind(i18n);
    expect(translateApiError(t, "cue_time must be HH:MM (24h) or empty")).toBe(
      "cue_time must be HH:MM (24h) or empty",
    );
  });
});
