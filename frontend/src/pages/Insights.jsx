import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "../api";

const METRICS = [
  { key: "successRate", value: (i) => `${i.success_rate}%` },
  { key: "habitStrength", value: (i) => `${i.habit_strength}/100` },
  {
    key: "bestTime",
    value: (i) => (i.best_hour !== null ? `${i.best_hour}:00` : "—"),
  },
  {
    key: "recovery",
    value: (i) => (i.avg_recovery_days ? `${i.avg_recovery_days}d` : "—"),
  },
];

export default function Insights() {
  const { t } = useTranslation();
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
      <h2>{t("insights.title")}</h2>
      <p className="science">{t("insights.science")}</p>
      {insights.length === 0 && <p>{t("insights.empty")}</p>}
      <div className="insights-grid">
        {insights.map((i) => (
          <div
            key={i.habit_id}
            className={`insight-card ${selected === i.habit_id ? "selected" : ""}`}
            onClick={() => select(i.habit_id)}
          >
            <h3>{i.name}</h3>
            {METRICS.map((m) => (
              <div className="metric" key={m.key}>
                <span>{t(`insights.${m.key}`)}</span>
                <strong>{m.value(i)}</strong>
              </div>
            ))}
          </div>
        ))}
      </div>
      {habit && (
        <div className="chart-section">
          <h3>{t("insights.consistency")}</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey="date" />
              <YAxis hide />
              <Tooltip />
              <Bar dataKey="completed" fill="#5e6ad2" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
