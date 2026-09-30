import { useTranslation } from "react-i18next";

const CARDS = ["tiny", "automaticity", "recovery"];

export default function Features() {
  const { t } = useTranslation();

  return (
    <section className="section" id="features">
      <h2>{t("features.title")}</h2>
      <p className="section-sub">{t("features.subtitle")}</p>
      <div className="features-grid">
        {CARDS.map((key) => (
          <article className="card" key={key}>
            <h3>{t(`features.${key}.title`)}</h3>
            <p>{t(`features.${key}.body`)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
