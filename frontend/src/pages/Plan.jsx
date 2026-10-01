import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";

export default function Plan() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const checkoutResult = searchParams.get("checkout"); // success | cancel
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .billingStatus()
      .then(setStatus)
      .catch((err) => setError(translateApiError(t, err.message)));
  }, []);

  const goTo = async (request) => {
    setError("");
    try {
      const { url } = await request();
      window.location.href = url;
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  const current = status?.plan || "free";
  const cards = ["free", "pro", "lifetime"];

  return (
    <div className="plan-page">
      <h1>{t("plan.title")}</h1>
      <p className="tagline">
        {t("plan.currentLabel")}: <strong>{t(`plan.${current}.name`)}</strong>
      </p>

      {checkoutResult === "success" && (
        <p className="notice">{t("plan.checkoutSuccess")}</p>
      )}
      {checkoutResult === "cancel" && (
        <p className="notice">{t("plan.checkoutCancel")}</p>
      )}
      {error && <p className="error">{error}</p>}

      <div className="plans">
        {cards.map((key) => (
          <div
            key={key}
            className={`plan-card ${current === key ? "is-current" : ""}`}
          >
            <h3>{t(`plan.${key}.name`)}</h3>
            <p className="price">
              {t(`plan.${key}.price`)}
              {key !== "free" && (
                <span className="period"> {t(`plan.${key}.period`)}</span>
              )}
            </p>
            <p className="plan-body">{t(`plan.${key}.body`)}</p>
            {current === key ? (
              <span className="plan-badge">{t("plan.currentBadge")}</span>
            ) : key === "free" ? (
              <span className="plan-badge muted">{t("plan.freeHint")}</span>
            ) : (
              <button
                type="button"
                className="btn-primary"
                onClick={() => goTo(() => api.checkout(key))}
              >
                {t(`plan.${key}.cta`)}
              </button>
            )}
          </div>
        ))}
      </div>

      {status?.has_customer && (
        <p>
          <button
            type="button"
            className="link"
            onClick={() => goTo(() => api.portal())}
          >
            {t("plan.manage")}
          </button>
        </p>
      )}
    </div>
  );
}
