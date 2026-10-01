import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, localDate } from "../api";
import HabitCard from "../components/HabitCard";
import RemindersToggle from "../components/RemindersToggle";

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [habits, setHabits] = useState([]);
  const [checkins, setCheckins] = useState({});
  const [streaks, setStreaks] = useState([]);
  const [ranges, setRanges] = useState({});
  const navigate = useNavigate();
  const today = localDate();

  const load = async () => {
    const [h, c, s] = await Promise.all([
      api.listHabits(),
      api.today(today),
      api.streaks(),
    ]);
    // One history request per habit (habit counts stay small).
    const r = await Promise.all(h.map((x) => api.range(x.id, 30)));

    setHabits(h);
    const map = {};
    c.forEach((x) => (map[x.habit_id] = x));
    setCheckins(map);
    setStreaks(s);
    setRanges(Object.fromEntries(h.map((x, i) => [x.id, r[i]])));
  };

  useEffect(() => {
    load();
  }, []);

  const checkin = async (habitId, completed, automaticity) => {
    await api.checkin(habitId, today, completed, automaticity);
    load();
  };

  const remove = async (id) => {
    await api.deleteHabit(id);
    load();
  };

  const headingDate = new Date().toLocaleDateString(i18n.language, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="dashboard">
      <div className="dashboard-head">
        <h2>
          {t("dashboard.today")} {headingDate}
        </h2>
        <RemindersToggle />
      </div>
      {habits.length === 0 && (
        <p>
          {t("dashboard.noHabits")}{" "}
          <a href="/new">{t("dashboard.createFirst")}</a>
        </p>
      )}
      {habits.map((h) => (
        <HabitCard
          key={h.id}
          habit={h}
          log={checkins[h.id]}
          streak={streaks.find((s) => s.habit_id === h.id)?.streak}
          logs={ranges[h.id] ?? []}
          onCheckin={checkin}
          onDelete={remove}
          onEdit={(id) => navigate(`/edit/${id}`)}
        />
      ))}
    </div>
  );
}
