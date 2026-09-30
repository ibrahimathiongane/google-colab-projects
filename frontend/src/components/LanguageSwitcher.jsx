import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", label: "EN" },
  { code: "fr", label: "FR" },
];

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();

  return (
    <div className="lang-switcher" role="group" aria-label={t("nav.language")}>
      {LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          className={i18n.language === code ? "active" : ""}
          aria-pressed={i18n.language === code}
          onClick={() => i18n.changeLanguage(code)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
