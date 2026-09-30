import { localDate } from "../api";

/**
 * 30-day activity grid for one habit. The API only returns days that have a
 * check-in row, so the missing days are rebuilt client-side as "not done".
 */
export default function MiniCalendar({ days = 30, logs = [] }) {
  const byDate = Object.fromEntries(logs.map((l) => [l.date, l.completed]));

  const cells = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const iso = localDate(d);
    cells.push({ iso, completed: byDate[iso] === true });
  }

  return (
    <div
      className="mini-calendar"
      role="img"
      aria-label={`Last ${days} days: ${cells.filter((c) => c.completed).length} done`}
    >
      {cells.map((c) => (
        <span
          key={c.iso}
          title={`${c.iso} — ${c.completed ? "done" : "missed"}`}
          className={`day ${c.completed ? "on" : "off"}`}
        />
      ))}
    </div>
  );
}
