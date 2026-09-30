import { useTranslation } from "react-i18next";

/**
 * "How automatic did this feel?" — the 1-10 self-report that feeds the
 * habit strength metric. Shown right after a check-in, skippable.
 */
export default function AutomaticityPrompt({ onPick, onSkip }) {
  const { t } = useTranslation();

  return (
    <div
      className="automaticity"
      role="group"
      aria-label={t("habit.howAutomatic")}
    >
      <span className="auto-label">{t("habit.howAutomatic")}</span>
      <div className="auto-scale">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            type="button"
            className="auto-btn"
            onClick={() => onPick(n)}
          >
            {n}
          </button>
        ))}
      </div>
      <button type="button" className="link" onClick={onSkip}>
        {t("habit.skip")}
      </button>
    </div>
  );
}
