import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Dashboard from "../pages/Dashboard";

vi.mock("../api", () => ({
  api: {
    listHabits: vi.fn(),
    today: vi.fn(),
    streaks: vi.fn(),
    checkin: vi.fn(),
    deleteHabit: vi.fn(),
  },
  localDate: () => "2026-09-30",
}));

const { api } = await import("../api");

const HABITS = [
  { id: 1, name: "Drink water", if_then: "After coffee, I drink one glass" },
];
const STREAKS = [{ habit_id: 1, streak: 4, completed_checkins: 5 }];

beforeEach(() => {
  vi.clearAllMocks();
  api.listHabits.mockResolvedValue(HABITS);
  api.today.mockResolvedValue([]);
  api.streaks.mockResolvedValue(STREAKS);
});

describe("Dashboard", () => {
  it("renders habits with their if-then and streak", async () => {
    render(<Dashboard />);

    expect(await screen.findByText("Drink water")).toBeInTheDocument();
    expect(screen.getByText(/After coffee/)).toBeInTheDocument();
    expect(screen.getByText(/4 day streak/)).toBeInTheDocument();
  });

  it("marks the habit as done using the local date", async () => {
    api.checkin.mockResolvedValue({});
    const user = userEvent.setup();
    render(<Dashboard />);
    await screen.findByText("Drink water");

    await user.click(screen.getByRole("button", { name: "✓ Done" }));

    await waitFor(() =>
      expect(api.checkin).toHaveBeenCalledWith(1, "2026-09-30", true, 5),
    );
    // The list is reloaded after the check-in.
    await waitFor(() => expect(api.listHabits).toHaveBeenCalledTimes(2));
  });

  it("shows the empty state when there is no habit yet", async () => {
    api.listHabits.mockResolvedValue([]);
    api.streaks.mockResolvedValue([]);
    render(<Dashboard />);

    expect(await screen.findByText(/No habits yet/)).toBeInTheDocument();
  });
});
