const API = "/api";
let token = localStorage.getItem("token");

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

async function req(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  register: (email, password, name) =>
    req("POST", "/users/register", { email, password, name }),
  login: (email, password) =>
    req("POST", "/users/login", { email, password }),
  me: () => req("GET", "/users/me"),

  listHabits: () => req("GET", "/habits/"),
  createHabit: (h) => req("POST", "/habits/", h),
  deleteHabit: (id) => req("DELETE", `/habits/${id}`),

  checkin: (habit_id, date, completed, automaticity, note) =>
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

  insights: () => req("GET", "/insights/summary"),
};
