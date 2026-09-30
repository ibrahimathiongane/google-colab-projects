import { useState, useEffect } from "react";
import { Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, setTokens } from "./api";
import LanguageSwitcher from "./components/LanguageSwitcher";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NewHabit from "./pages/NewHabit";
import Insights from "./pages/Insights";
import EditHabit from "./pages/EditHabit";

export default function App() {
  const { t } = useTranslation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (localStorage.getItem("token")) {
      api
        .me()
        .then(setUser)
        .catch(() => setTokens({}))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const logout = async () => {
    try {
      await api.logout(); // revoke the refresh token server-side
    } catch {
      /* best effort: local state is cleared anyway */
    }
    setTokens({});
    setUser(null);
    navigate("/login");
  };

  if (loading) return <div className="loading">{t("app.loading")}</div>;

  return (
    <div className="app">
      {user && (
        <nav className="nav">
          <span className="logo">🌱 Habit Tracker</span>
          <Link to="/">{t("nav.dashboard")}</Link>
          <Link to="/new">{t("nav.newHabit")}</Link>
          <Link to="/insights">{t("nav.insights")}</Link>
          <LanguageSwitcher />
          <button onClick={logout}>{t("nav.logout")}</button>
        </nav>
      )}
      <Routes>
        <Route
          path="/login"
          element={
            <Login
              onLogin={(u, payload) => {
                setTokens(payload);
                setUser(u);
                navigate("/");
              }}
            />
          }
        />
        <Route
          path="/"
          element={user ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/new"
          element={user ? <NewHabit /> : <Navigate to="/login" />}
        />
        <Route
          path="/edit/:id"
          element={user ? <EditHabit /> : <Navigate to="/login" />}
        />
        <Route
          path="/insights"
          element={user ? <Insights /> : <Navigate to="/login" />}
        />
      </Routes>
    </div>
  );
}
