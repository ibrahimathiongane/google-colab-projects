import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";
import { useNavigate } from "react-router-dom";

export default function NewHabit() {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [anchor, setAnchor] = useState("");
  const [tinyBehavior, setTinyBehavior] = useState("");
  const [celebration, setCelebration] = useState("");
  const [cueTime, setCueTime] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const steps = [
    { key: "anchor", value: anchor, set: setAnchor },
    { key: "behavior", value: tinyBehavior, set: setTinyBehavior },
    { key: "celebration", value: celebration, set: setCelebration },
  ];
  const current = steps[step];

  const submit = async () => {
    setError("");
    try {
      await api.createHabit({
        name,
        anchor,
        tiny_behavior: tinyBehavior,
        celebration,
        cue_time: cueTime,
      });
      navigate("/");
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  return (
    <div className="wizard">
      <h2>{t("wizard.title")}</h2>
      <p className="science">{t("wizard.science")}</p>
      <div className="steps-indicator">
        {steps.map((s) => (
          <span key={s.key} className={s.key === current.key ? "active" : ""}>
            ●
          </span>
        ))}
      </div>
      <h3>{t(`wizard.steps.${current.key}.title`)}</h3>
      <p>{t(`wizard.steps.${current.key}.desc`)}</p>
      {step === 0 && (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("wizard.namePlaceholder")}
          aria-label={t("edit.fields.name")}
        />
      )}
      <input
        value={current.value}
        onChange={(e) => current.set(e.target.value)}
        placeholder={t(`wizard.steps.${current.key}.placeholder`)}
      />
      {step === 2 && (
        <input
          value={cueTime}
          onChange={(e) => setCueTime(e.target.value)}
          placeholder={t("wizard.cueTime")}
        />
      )}
      {error && <p className="error">{error}</p>}
      <div className="wizard-nav">
        {step > 0 && (
          <button onClick={() => setStep(step - 1)}>{t("wizard.back")}</button>
        )}
        {step < 2 && (
          <button
            className="btn-primary"
            onClick={() => setStep(step + 1)}
            disabled={
              step === 0
                ? !name.trim() || !steps[0].value.trim()
                : !current.value.trim()
            }
          >
            {t("wizard.next")}
          </button>
        )}
        {step === 2 && (
          <button className="btn-primary" onClick={submit} disabled={!celebration}>
            {t("wizard.create")}
          </button>
        )}
      </div>
    </div>
  );
}
