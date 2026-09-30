import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import fr from "./fr.json";

export const SUPPORTED_LANGUAGES = ["en", "fr"];
export const STORAGE_KEY = "lang";

function detectLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED_LANGUAGES.includes(saved)) return saved;
  } catch {
    /* storage unavailable (private mode): fall through to navigator */
  }
  const nav = typeof navigator !== "undefined" ? navigator.language : "en";
  return nav?.toLowerCase().startsWith("fr") ? "fr" : "en";
}

function applyDocumentLanguage(lng) {
  if (typeof document === "undefined") return;
  document.documentElement.lang = lng;
  document.title = i18n.t("app.title");
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: detectLanguage(),
  fallbackLng: "en",
  supportedLngs: SUPPORTED_LANGUAGES,
  interpolation: { escapeValue: false }, // React already escapes output
  returnNull: false,
  load: "languageOnly",
});

i18n.on("languageChanged", (lng) => {
  try {
    localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    /* persistence is best-effort */
  }
  applyDocumentLanguage(lng);
});
applyDocumentLanguage(i18n.language);

export default i18n;
