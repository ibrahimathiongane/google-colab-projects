import { useState, useEffect } from "react";
import { api, localDate } from "../api";

export default function Dashboard() {
  const [habits, setHabits] = useState([]);
  const [checkins, setCheckins] = useState({});
  const [streaks, setStreaks] = useState([]);
  const today = localDate();

  const load = async () => {
    const [h, c, s] = await Promise.all([
      api.listHabits(),
      api.today(today),
      api.streaks(),
    ]);
    setHabits(h);
    const map = {};
    c.forEach((x) => (map[x.habit_id] = x));
    setCheckins(map);
    setStreaks(s);
  };

  useEffect(() => {
    load();
  }, []);

  const checkin = async (habitId, completed) => {
    await api.checkin(habitId, today, completed, 5);
    load();
  };

  const remove = async (id) => {
    await api.deleteHabit(id);
    load();
  };

  return (
    <div className="dashboard">
      <h2>
        Today —{" "}
        {new Date().toLocaleDateString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
      </h2>
      {habits.length === 0 && (
        <p>
          No habits yet.{" "}
          <a href="/new">Create your first tiny habit →</a>
        </p>
      )}
      {habits.map((h) => {
        const c = checkins[h.id];
        const streak = streaks.find((s) => s.habit_id === h.id);
        return (
          <div key={h.id} className={`habit-card ${c?.completed ? "done" : ""}`}>
            <div className="habit-info">
              <h3>{h.name}</h3>
              <p className="if-then">&ldquo;{h.if_then}&rdquo;</p>
              {streak && (
                <span className="streak">🔥 {streak.streak} day streak</span>
              )}
            </div>
            <div className="habit-actions">
              {!c?.completed && (
                <button
                  className="btn-done"
                  onClick={() => checkin(h.id, true)}
                >
                  ✓ Done
                </button>
              )}
              {c?.completed && (
                <button
                  className="btn-undo"
                  onClick={() => checkin(h.id, false)}
                >
                  Undo
                </button>
              )}
              <button
                className="btn-delete"
                onClick={() => remove(h.id)}
              >
                ×
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
