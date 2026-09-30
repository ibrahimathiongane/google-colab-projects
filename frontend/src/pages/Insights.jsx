import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "../api";

export default function Insights() {
  const [insights, setInsights] = useState([]);
  const [selected, setSelected] = useState(null);
  const [range, setRange] = useState([]);

  useEffect(() => {
    api.insights().then((data) => {
      setInsights(data);
      if (data.length) {
        setSelected(data[0].habit_id);
        api.range(data[0].habit_id, 30).then(setRange);
      }
    });
  }, []);

  const select = async (id) => {
    setSelected(id);
    const r = await api.range(id, 30);
    setRange(r);
  };

  const habit = insights.find((i) => i.habit_id === selected);
  const chartData = range.map((r) => ({
    date: r.date.slice(5),
    completed: r.completed ? 1 : 0,
  }));

  return (
    <div className="insights">
      <h2>Insights</h2>
      <p className="science">
        Habit science: consistency beats intensity. Track your recovery rate,
        not just streaks.
      </p>
      {insights.length === 0 && <p>No data yet. Start checking in!</p>}
      <div className="insights-grid">
        {insights.map((i) => (
          <div
            key={i.habit_id}
            className={`insight-card ${selected === i.habit_id ? "selected" : ""}`}
            onClick={() => select(i.habit_id)}
          >
            <h3>{i.name}</h3>
            <div className="metric">
              <span>Success rate</span>
              <strong>{i.success_rate}%</strong>
            </div>
            <div className="metric">
              <span>Habit strength</span>
              <strong>{i.habit_strength}/100</strong>
            </div>
            <div className="metric">
              <span>Best time</span>
              <strong>
                {i.best_hour !== null ? `${i.best_hour}:00` : "—"}
              </strong>
            </div>
            <div className="metric">
              <span>Recovery rate</span>
              <strong>
                {i.avg_recovery_days ? `${i.avg_recovery_days}d` : "—"}
              </strong>
            </div>
          </div>
        ))}
      </div>
      {habit && (
        <div className="chart-section">
          <h3>Consistency — last 30 days</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey="date" />
              <YAxis hide />
              <Tooltip />
              <Bar dataKey="completed" fill="#4caf50" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
