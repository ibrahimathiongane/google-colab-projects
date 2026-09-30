import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./LanguageSwitcher";

export default function Nav({ appUrl }) {
  const { t } = useTranslation();

  return (
    <header className="nav">
      <a className="logo" href="#top">
        🌱 Habit Tracker
      </a>
      <nav className="nav-links" aria-label="Sections">
        <a href="#features">{t("nav.features")}</a>
        <a href="#science">{t("nav.science")}</a>
        <a href="#pricing">{t("nav.pricing")}</a>
      </nav>
      <div className="nav-actions">
        <LanguageSwitcher />
        <a className="btn btn-primary" href={appUrl}>
          {t("nav.openApp")}
        </a>
      </div>
    </header>
  );
}
