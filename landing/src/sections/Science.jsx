import { useTranslation } from "react-i18next";

export default function Science() {
  const { t } = useTranslation();

  return (
    <section className="section science" id="science">
      <div className="science-copy">
        <h2>{t("science.title")}</h2>
        <p>{t("science.body")}</p>
      </div>
      <figure className="shot">
        <img
          src="/images/insights.png"
          alt={t("science.screenshotAlt")}
          width={1280}
          height={900}
        />
      </figure>
    </section>
  );
}
