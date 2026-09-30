import { useTranslation } from "react-i18next";
import { localDate } from "../api";

/**
 * 30-day activity grid for one habit. The API only returns days that have a
 * check-in row, so the missing days are rebuilt client-side as "not done".
 */
export default function MiniCalendar({ days = 30, logs = [] }) {
  const { t } = useTranslation();
  const byDate = Object.fromEntries(logs.map((l) => [l.date, l.completed]));

  const cells = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const iso = localDate(d);
    cells.push({ iso, completed: byDate[iso] === true });
  }
  const done = cells.filter((c) => c.completed).length;

  return (
    <div
      className="mini-calendar"
      role="img"
      aria-label={t("habit.calendarLabel", { count: days, done })}
    >
      {cells.map((c) => (
        <span
          key={c.iso}
          title={t(c.completed ? "habit.dayDone" : "habit.dayMissed", {
            date: c.iso,
          })}
          className={`day ${c.completed ? "on" : "off"}`}
        />
      ))}
    </div>
  );
}
