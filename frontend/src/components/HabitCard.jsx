import { useState } from "react";
import { useTranslation } from "react-i18next";
import AutomaticityPrompt from "./AutomaticityPrompt";
import MiniCalendar from "./MiniCalendar";

export default function HabitCard({
  habit,
  log,
  streak,
  logs,
  onCheckin,
  onDelete,
  onEdit,
}) {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState(false);

  const completed = Boolean(log?.completed);
  // Ask for the 1-10 self-report until it is answered (or skipped today).
  const showPrompt = completed && !log?.automaticity && !dismissed;

  const handleDelete = () => {
    if (window.confirm(t("habit.deleteConfirm", { name: habit.name }))) {
      onDelete(habit.id);
    }
  };

  return (
    <div className={`habit-card ${completed ? "done" : ""}`}>
      <div className="habit-info">
        <h3>{habit.name}</h3>
        <p className="if-then">&ldquo;{habit.if_then}&rdquo;</p>
        {streak !== undefined && (
          <span className="streak">
            🔥 {t("habit.streak", { count: streak })}
          </span>
        )}
        <MiniCalendar logs={logs} />
        {showPrompt && (
          <AutomaticityPrompt
            onPick={(n) => {
              setDismissed(false);
              onCheckin(habit.id, true, n);
            }}
            onSkip={() => setDismissed(true)}
          />
        )}
        {completed && log?.automaticity && (
          <span className="auto-badge" title={t("insights.habitStrength")}>
            {t("habit.automaticity", { value: log.automaticity })}
          </span>
        )}
      </div>
      <div className="habit-actions">
        {!completed && (
          <button
            className="btn-done"
            onClick={() => onCheckin(habit.id, true, null)}
          >
            {t("habit.done")}
          </button>
        )}
        {completed && (
          <button
            className="btn-undo"
            onClick={() => onCheckin(habit.id, false, null)}
          >
            {t("habit.undo")}
          </button>
        )}
        <button className="btn-edit" onClick={() => onEdit(habit.id)}>
          {t("habit.edit")}
        </button>
        <button className="btn-delete" onClick={handleDelete}>
          ×
        </button>
      </div>
    </div>
  );
}
