import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { translateApiError } from "../i18n/apiErrors";

export default function Login({ onLogin }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = isRegister
        ? await api.register(email, password, name)
        : await api.login(email, password);
      onLogin(res.user || { email }, {
        token: res.token,
        refresh_token: res.refresh_token,
      });
    } catch (err) {
      setError(translateApiError(t, err.message));
    }
  };

  return (
    <div className="auth">
      <h1>🌱 Habit Tracker</h1>
      <p className="tagline">{t("login.tagline")}</p>
      <form onSubmit={submit}>
        {isRegister && (
          <input
            placeholder={t("login.name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <input
          placeholder={t("login.email")}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          placeholder={t("login.password")}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" className="btn-primary">
          {isRegister ? t("login.createAccount") : t("login.login")}
        </button>
      </form>
      <p>
        <button className="link" onClick={() => setIsRegister(!isRegister)}>
          {isRegister ? t("login.haveAccount") : t("login.needAccount")}
        </button>
      </p>
    </div>
  );
}
