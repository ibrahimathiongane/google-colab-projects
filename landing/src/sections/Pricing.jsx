import { useTranslation } from "react-i18next";

const PLANS = ["free", "pro", "lifetime"];

export default function Pricing({ appUrl }) {
  const { t } = useTranslation();

  return (
    <section className="section" id="pricing">
      <h2>{t("pricing.title")}</h2>
      <p className="section-sub">{t("pricing.subtitle")}</p>
      <div className="pricing-grid">
        {PLANS.map((plan) => {
          const soon = plan !== "free";
          const href = soon ? undefined : `${appUrl}/login`;
          return (
            <article
              className={`card plan ${plan === "pro" ? "featured" : ""}`}
              key={plan}
            >
              <h3>{t(`pricing.${plan}.name`)}</h3>
              <p className="price">
                {t(`pricing.${plan}.price`)}{" "}
                <span className="period">{t(`pricing.${plan}.period`)}</span>
              </p>
              <p className="plan-body">{t(`pricing.${plan}.body`)}</p>
              {soon ? (
                <span className="btn btn-soon" aria-disabled="true">
                  {t(`pricing.${plan}.cta`)}
                </span>
              ) : (
                <a className="btn btn-primary" href={href}>
                  {t(`pricing.${plan}.cta`)}
                </a>
              )}
            </article>
          );
        })}
      </div>
      <p className="pricing-note">{t("pricing.note")}</p>
    </section>
  );
}
