import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard";

function iso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const TODAY = iso(new Date());
const YESTERDAY = iso(new Date(Date.now() - 24 * 60 * 60 * 1000));

vi.mock("../api", async () => {
  const realLocalDate = (d = new Date()) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };
  return {
    api: {
      listHabits: vi.fn(),
      today: vi.fn(),
      streaks: vi.fn(),
      range: vi.fn(),
      checkin: vi.fn(),
      deleteHabit: vi.fn(),
    },
    localDate: realLocalDate,
  };
});

const { api } = await import("../api");

const HABITS = [
  { id: 1, name: "Drink water", if_then: "After coffee, I drink one glass" },
];
const STREAKS = [{ habit_id: 1, streak: 4, completed_checkins: 5 }];
const RANGE = [
  { date: YESTERDAY, completed: true, automaticity: 7 },
  { date: TODAY, completed: false, automaticity: null },
];

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.listHabits.mockResolvedValue(HABITS);
  api.streaks.mockResolvedValue(STREAKS);
  api.range.mockResolvedValue(RANGE);
  api.deleteHabit.mockResolvedValue({ ok: true });
  api.today.mockResolvedValue([]);
  // A check-in flips today's row, like the real API upsert does.
  api.checkin.mockImplementation(async (habitId, date, completed, automaticity) => {
    api.today.mockResolvedValue([
      { habit_id: habitId, completed, automaticity },
    ]);
    return { ok: true };
  });
});

describe("Dashboard", () => {
  it("renders habits with their if-then, streak and calendar", async () => {
    renderDashboard();

    expect(await screen.findByText("Drink water")).toBeInTheDocument();
    expect(screen.getByText(/After coffee/)).toBeInTheDocument();
    expect(screen.getByText(/4 day streak/)).toBeInTheDocument();
    // 30 days, one of them done.
    const cells = document.querySelectorAll(".mini-calendar .day");
    expect(cells).toHaveLength(30);
    expect(document.querySelectorAll(".mini-calendar .day.on")).toHaveLength(1);
  });

  it("sends NO fake automaticity when checking in", async () => {
    // Regression: the rating used to be hard-coded to 5, which poisoned
    // the habit strength metric.
    renderDashboard();
    await screen.findByText("Drink water");

    await userEvent.click(screen.getByRole("button", { name: "✓ Done" }));

    await waitFor(() =>
      expect(api.checkin).toHaveBeenCalledWith(1, TODAY, true, null),
    );
  });

  it("asks for the self-report after a check-in and stores the answer", async () => {
    renderDashboard();
    await screen.findByText("Drink water");

    await userEvent.click(screen.getByRole("button", { name: "✓ Done" }));
    await screen.findByText("How automatic did this feel?");

    await userEvent.click(screen.getByRole("button", { name: "7" }));
    await waitFor(() =>
      expect(api.checkin).toHaveBeenCalledWith(1, TODAY, true, 7),
    );
  });

  it("skips the self-report without blocking", async () => {
    renderDashboard();
    await screen.findByText("Drink water");
    await userEvent.click(screen.getByRole("button", { name: "✓ Done" }));
    await screen.findByText("How automatic did this feel?");

    await userEvent.click(screen.getByRole("button", { name: "Skip" }));

    expect(screen.queryByText("How automatic did this feel?")).toBeNull();
    expect(api.checkin).toHaveBeenCalledTimes(1); // no extra call
  });

  it("shows the stored rating instead of the prompt", async () => {
    api.today.mockResolvedValue([
      { habit_id: 1, completed: true, automaticity: 8 },
    ]);
    renderDashboard();

    expect(await screen.findByText("automaticity 8/10")).toBeInTheDocument();
    expect(screen.queryByText("How automatic did this feel?")).toBeNull();
  });

  it("shows the empty state when there is no habit yet", async () => {
    api.listHabits.mockResolvedValue([]);
    api.streaks.mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByText(/No habits yet/)).toBeInTheDocument();
  });
});
