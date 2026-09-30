import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";

const FIELDS = ["name", "anchor", "tiny_behavior", "celebration", "cue_time"];

export default function EditHabit() {
  const { t } = useTranslation();
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
          setError(t("edit.notFound"));
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
      .catch((err) => setError(translateApiError(t, err.message)));
  }, [id, t]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.updateHabit(Number(id), form);
      navigate("/");
    } catch (err) {
      setError(translateApiError(t, err.message));
      setSaving(false);
    }
  };

  if (!form) {
    return (
      <div className="edit-habit">
        <h2>{t("edit.title")}</h2>
        {error && <p className="error">{error}</p>}
        {!error && <p>{t("edit.loading")}</p>}
        {error && <a href="/">{t("edit.back")}</a>}
      </div>
    );
  }

  return (
    <div className="edit-habit">
      <h2>{t("edit.title")}</h2>
      <p className="science">{t("edit.science")}</p>
      <form onSubmit={submit}>
        {FIELDS.map((key) => (
          <label key={key}>
            {t(`edit.fields.${key}`)}
            <input
              value={form[key]}
              placeholder={t(`edit.placeholders.${key}`)}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ))}
        {error && <p className="error">{error}</p>}
        <div className="wizard-nav">
          <button type="button" onClick={() => navigate("/")}>
            {t("edit.cancel")}
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? t("edit.saving") : t("edit.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
