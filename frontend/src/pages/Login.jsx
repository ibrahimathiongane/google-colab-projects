import { useState } from "react";
import { api } from "../api";

export default function Login({ onLogin }) {
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
      onLogin(res.user || { email }, res.token);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="auth">
      <h1>🌱 Habit Tracker</h1>
      <p className="tagline">
        Build habits that stick — the science-based way
      </p>
      <form onSubmit={submit}>
        {isRegister && (
          <input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <input
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit">
          {isRegister ? "Create account" : "Login"}
        </button>
      </form>
      <p>
        <button className="link" onClick={() => setIsRegister(!isRegister)}>
          {isRegister
            ? "Already have an account? Login"
            : "Need an account? Register"}
        </button>
      </p>
    </div>
  );
}
