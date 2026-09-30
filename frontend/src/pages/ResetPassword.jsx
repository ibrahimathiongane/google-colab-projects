import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError(t("reset.mismatch"));
      return;
    }
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  return (
    <div className="auth">
      <h1>🌱 Habit Tracker</h1>
      {done ? (
        <>
          <p className="tagline">{t("reset.success")}</p>
          <Link className="btn-primary" to="/login">
            {t("login.login")}
          </Link>
        </>
      ) : !token ? (
        <>
          <p className="tagline">{t("reset.missingToken")}</p>
          <Link className="btn-primary" to="/forgot-password">
            {t("reset.requestNew")}
          </Link>
        </>
      ) : (
        <>
          <p className="tagline">{t("reset.title")}</p>
          <form onSubmit={submit}>
            <input
              placeholder={t("reset.password")}
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <input
              placeholder={t("reset.confirm")}
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
            {error && <p className="error">{error}</p>}
            <button type="submit" className="btn-primary">
              {t("reset.submit")}
            </button>
          </form>
          <p>
            <Link className="link" to="/login">
              {t("forgot.backToLogin")}
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
