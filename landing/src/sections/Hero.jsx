import { useTranslation } from "react-i18next";

export default function Hero({ appUrl }) {
  const { t } = useTranslation();

  return (
    <section className="hero" id="top">
      <h1>{t("hero.title")}</h1>
      <p className="hero-sub">{t("hero.subtitle")}</p>
      <div className="hero-ctas">
        <a className="btn btn-primary" href={`${appUrl}/login`}>
          {t("hero.ctaPrimary")}
        </a>
        <a className="btn" href="#science">
          {t("hero.ctaSecondary")}
        </a>
      </div>
      <figure className="shot">
        <img
          src="/images/dashboard.png"
          alt={t("hero.screenshotAlt")}
          width={1280}
          height={900}
        />
      </figure>
    </section>
  );
}
