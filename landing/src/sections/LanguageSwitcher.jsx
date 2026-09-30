import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "../i18n";

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();

  return (
    <div className="lang-switcher" role="group" aria-label={t("nav.openApp")}>
      {SUPPORTED_LANGUAGES.map((lng) => (
        <button
          key={lng}
          type="button"
          className={i18n.language === lng ? "active" : ""}
          onClick={() => i18n.changeLanguage(lng)}
          aria-pressed={i18n.language === lng}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
