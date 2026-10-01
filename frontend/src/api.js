// Same-origin "/api" on the web. The Capacitor shell loads the bundle from
// a local WebView (origin localhost), so the API origin is baked at build
// time: VITE_API_URL=https://app.example.com (no trailing slash).
const API = `${import.meta.env.VITE_API_URL ?? ""}/api`;

let token = localStorage.getItem("token");
let refreshToken = localStorage.getItem("refresh_token");

export function setTokens({ token: t, refresh_token: rt }) {
  token = t || null;
  refreshToken = rt || null;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
  if (rt) localStorage.setItem("refresh_token", rt);
  else localStorage.removeItem("refresh_token");
}

/** Today's date in the *user's* timezone (YYYY-MM-DD), not UTC. */
export function localDate(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Local UTC offset in minutes, for server-side hour formatting. */
export function tzOffset() {
  return -new Date().getTimezoneOffset();
}

async function tryRefresh() {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API}/users/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      setTokens({});
      return false;
    }
    setTokens(await res.json());
    return true;
  } catch {
    return false;
  }
}

async function req(method, path, body, retried = false) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  // Access token expired: refresh once transparently, then retry.
  if (res.status === 401 && !retried && (await tryRefresh())) {
    return req(method, path, body, true);
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail
              .map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`)
              .join(", ")
          : res.statusText;
    const err = new Error(detail || res.statusText);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  register: (email, password, name) =>
    req("POST", "/users/register", { email, password, name }),
  login: (email, password) =>
    req("POST", "/users/login", { email, password }),
  logout: () =>
    refreshToken
      ? req("POST", "/users/logout", { refresh_token: refreshToken })
      : Promise.resolve(),
  me: () => req("GET", "/users/me"),
  forgotPassword: (email) =>
    req("POST", "/users/forgot-password", { email }),
  resetPassword: (token, password) =>
    req("POST", "/users/reset-password", { token, password }),

  billingStatus: () => req("GET", "/billing/"),
  checkout: (plan) => req("POST", "/billing/checkout", { plan }),
  portal: () => req("POST", "/billing/portal"),

  remindersStatus: () => req("GET", "/notifications/"),
  remindersPublicKey: () => req("GET", "/notifications/vapid-public-key"),
  remindersSubscribe: (payload) =>
    req("POST", "/notifications/subscribe", payload),
  remindersUnsubscribe: (endpoint) =>
    req("POST", "/notifications/unsubscribe", { endpoint }),

  listHabits: () => req("GET", "/habits/"),
  createHabit: (h) => req("POST", "/habits/", h),
  updateHabit: (id, payload) => req("PUT", `/habits/${id}`, payload),
  deleteHabit: (id) => req("DELETE", `/habits/${id}`),

  checkin: (habit_id, date, completed, automaticity, note = "") =>
    req("POST", "/tracking/checkin", {
      habit_id,
      date,
      completed,
      automaticity,
      note,
    }),
  today: (date) => req("GET", `/tracking/today?date=${date}`),
  range: (habit_id, days) =>
    req("GET", `/tracking/range?habit_id=${habit_id}&days=${days}`),
  streaks: () => req("GET", "/tracking/streaks"),

  insights: () => req("GET", `/insights/summary?tz_offset=${tzOffset()}`),
};
