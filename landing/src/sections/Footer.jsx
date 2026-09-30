import { useTranslation } from "react-i18next";

export default function Footer({ appUrl }) {
  const { t } = useTranslation();

  return (
    <footer className="footer">
      <span className="logo">🌱 Habit Tracker</span>
      <p>{t("footer.tagline")}</p>
      <div className="footer-links">
        <a href={appUrl}>{t("footer.app")}</a>
        <span className="copyright">{t("footer.copyright")}</span>
      </div>
    </footer>
  );
}
