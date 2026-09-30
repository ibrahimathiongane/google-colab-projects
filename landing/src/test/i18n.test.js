import { afterEach, describe, expect, it } from "vitest";
import i18n from "../i18n";

afterEach(async () => {
  await i18n.changeLanguage("en");
  localStorage.removeItem("lang");
});

describe("landing dictionaries", () => {
  it("keeps EN and FR key-for-key identical", async () => {
    await i18n.changeLanguage("en");
    expect(i18n.t("nav.openApp")).toBe("Open app");

    await i18n.changeLanguage("fr");
    expect(i18n.t("nav.openApp")).toBe("Ouvrir l'app");

    const flatten = (obj, prefix = "") =>
      Object.entries(obj).flatMap(([k, v]) =>
        typeof v === "object"
          ? flatten(v, `${prefix}${k}.`)
          : [`${prefix}${k}`],
      );
    const enKeys = flatten(i18n.getResource("en", "translation")).sort();
    const frKeys = flatten(i18n.getResource("fr", "translation")).sort();
    expect(frKeys).toEqual(enKeys);
    expect(enKeys.length).toBeGreaterThan(25);
  });

  it("persists the choice and updates <html lang> + document.title", async () => {
    await i18n.changeLanguage("fr");
    expect(localStorage.getItem("lang")).toBe("fr");
    expect(document.documentElement.lang).toBe("fr");
    expect(document.title).toBe(i18n.t("app.title"));
  });
});
