import { useTranslation } from "react-i18next";

const PLANS = [
  { key: "free", path: "/login" },
  { key: "pro", path: "/plan" },
  { key: "lifetime", path: "/plan" },
];

export default function Pricing({ appUrl }) {
  const { t } = useTranslation();

  return (
    <section className="section" id="pricing">
      <h2>{t("pricing.title")}</h2>
      <p className="section-sub">{t("pricing.subtitle")}</p>
      <div className="pricing-grid">
        {PLANS.map(({ key, path }) => (
          <article
            className={`card plan ${key === "pro" ? "featured" : ""}`}
            key={key}
          >
            <h3>{t(`pricing.${key}.name`)}</h3>
            <p className="price">
              {t(`pricing.${key}.price`)}{" "}
              <span className="period">{t(`pricing.${key}.period`)}</span>
            </p>
            <p className="plan-body">{t(`pricing.${key}.body`)}</p>
            <a className="btn btn-primary" href={`${appUrl}${path}`}>
              {t(`pricing.${key}.cta`)}
            </a>
          </article>
        ))}
      </div>
      <p className="pricing-note">{t("pricing.note")}</p>
    </section>
  );
}
