import { useState, useEffect } from "react";
import { Routes, Route, Navigate, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, setTokens } from "./api";
import LanguageSwitcher from "./components/LanguageSwitcher";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Plan from "./pages/Plan";
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
          <NavLink to="/">{t("nav.dashboard")}</NavLink>
          <NavLink to="/new">{t("nav.newHabit")}</NavLink>
          <NavLink to="/insights">{t("nav.insights")}</NavLink>
          <NavLink to="/plan">{t("nav.plan")}</NavLink>
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
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
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
        <Route
          path="/plan"
          element={user ? <Plan /> : <Navigate to="/login" />}
        />
      </Routes>
    </div>
  );
}
