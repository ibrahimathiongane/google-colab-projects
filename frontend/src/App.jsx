import { useState, useEffect } from "react";
import { Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import { api, setToken } from "./api";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NewHabit from "./pages/NewHabit";
import Insights from "./pages/Insights";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const t = localStorage.getItem("token");
    if (t) {
      setToken(t);
      api
        .me()
        .then(setUser)
        .catch(() => setToken(null))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="app">
      {user && (
        <nav className="nav">
          <span className="logo">🌱 Habit Tracker</span>
          <Link to="/">Dashboard</Link>
          <Link to="/new">New Habit</Link>
          <Link to="/insights">Insights</Link>
          <button
            onClick={() => {
              setToken(null);
              setUser(null);
              navigate("/login");
            }}
          >
            Logout
          </button>
        </nav>
      )}
      <Routes>
        <Route
          path="/login"
          element={
            <Login
              onLogin={(u, t) => {
                setToken(t);
                setUser(u);
                navigate("/");
              }}
            />
          }
        />
        <Route
          path="/"
          element={user ? <Dashboard user={user} /> : <Navigate to="/login" />}
        />
        <Route
          path="/new"
          element={user ? <NewHabit /> : <Navigate to="/login" />}
        />
        <Route
          path="/insights"
          element={user ? <Insights /> : <Navigate to="/login" />}
        />
      </Routes>
    </div>
  );
}
