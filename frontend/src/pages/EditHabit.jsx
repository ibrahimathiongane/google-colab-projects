import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

const FIELDS = [
  { key: "name", label: "Name", placeholder: "e.g., Drink water" },
  { key: "anchor", label: "Anchor", placeholder: "e.g., pour my morning coffee" },
  {
    key: "tiny_behavior",
    label: "Tiny behavior",
    placeholder: "e.g., drink one glass",
  },
  {
    key: "celebration",
    label: "Celebration",
    placeholder: "e.g., smile and say yes",
  },
  { key: "cue_time", label: "Cue time", placeholder: "08:00 (optional)" },
];

export default function EditHabit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .listHabits()
      .then((habits) => {
        const found = habits.find((h) => h.id === Number(id));
        if (!found) {
          setError("Habit not found");
        } else {
          setForm({
            name: found.name,
            anchor: found.anchor,
            tiny_behavior: found.tiny_behavior,
            celebration: found.celebration,
            cue_time: found.cue_time,
          });
        }
      })
      .catch((err) => setError(err.message));
  }, [id]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.updateHabit(Number(id), form);
      navigate("/");
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  if (!form) {
    return (
      <div className="edit-habit">
        <h2>Edit habit</h2>
        {error && <p className="error">{error}</p>}
        {!error && <p>Loading…</p>}
        {error && <a href="/">← Back to dashboard</a>}
      </div>
    );
  }

  return (
    <div className="edit-habit">
      <h2>Edit habit</h2>
      <p className="science">
        The if-then sentence is regenerated from your answers.
      </p>
      <form onSubmit={submit}>
        {FIELDS.map((f) => (
          <label key={f.key}>
            {f.label}
            <input
              value={form[f.key]}
              placeholder={f.placeholder}
              onChange={(e) =>
                setForm({ ...form, [f.key]: e.target.value })
              }
            />
          </label>
        ))}
        {error && <p className="error">{error}</p>}
        <div className="wizard-nav">
          <button type="button" onClick={() => navigate("/")}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
