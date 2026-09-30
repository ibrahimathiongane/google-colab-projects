import { useState } from "react";
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
  const [dismissed, setDismissed] = useState(false);

  const completed = Boolean(log?.completed);
  // Ask for the 1-10 self-report until it is answered (or skipped today).
  const showPrompt = completed && !log?.automaticity && !dismissed;

  const handleDelete = () => {
    if (window.confirm(`Delete "${habit.name}"? Its history stays in Insights.`)) {
      onDelete(habit.id);
    }
  };

  return (
    <div className={`habit-card ${completed ? "done" : ""}`}>
      <div className="habit-info">
        <h3>{habit.name}</h3>
        <p className="if-then">&ldquo;{habit.if_then}&rdquo;</p>
        {streak !== undefined && (
          <span className="streak">🔥 {streak} day streak</span>
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
          <span className="auto-badge" title="Habit strength input">
            automaticity {log.automaticity}/10
          </span>
        )}
      </div>
      <div className="habit-actions">
        {!completed && (
          <button
            className="btn-done"
            onClick={() => onCheckin(habit.id, true, null)}
          >
            ✓ Done
          </button>
        )}
        {completed && (
          <button
            className="btn-undo"
            onClick={() => onCheckin(habit.id, false, null)}
          >
            Undo
          </button>
        )}
        <button className="btn-edit" onClick={() => onEdit(habit.id)}>
          ✎ Edit
        </button>
        <button className="btn-delete" onClick={handleDelete}>
          ×
        </button>
      </div>
    </div>
  );
}
