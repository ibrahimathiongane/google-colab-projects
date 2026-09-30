import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  return (
    <div className="auth">
      <h1>🌱 Habit Tracker</h1>
      {sent ? (
        <>
          <p className="tagline">{t("forgot.sent")}</p>
          <Link className="btn-primary" to="/login">
            {t("forgot.backToLogin")}
          </Link>
        </>
      ) : (
        <>
          <p className="tagline">{t("forgot.intro")}</p>
          <form onSubmit={submit}>
            <input
              placeholder={t("login.email")}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <p className="error">{error}</p>}
            <button type="submit" className="btn-primary">
              {t("forgot.submit")}
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
