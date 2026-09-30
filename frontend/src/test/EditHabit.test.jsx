import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import EditHabit from "../pages/EditHabit";

vi.mock("../api", () => ({
  api: {
    listHabits: vi.fn(),
    updateHabit: vi.fn(),
  },
  localDate: () => "2026-09-30",
}));

const { api } = await import("../api");

const HABIT = {
  id: 1,
  name: "Drink water",
  anchor: "after coffee",
  tiny_behavior: "drink one glass",
  celebration: "smile",
  cue_time: "08:30",
  if_then: "After I after coffee, I will drink one glass, then I will smile.",
  created_at: "2026-09-01T10:00:00",
};

function renderEdit() {
  return render(
    <MemoryRouter initialEntries={["/edit/1"]}>
      <Routes>
        <Route path="/edit/:id" element={<EditHabit />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EditHabit", () => {
  it("prefills the form from the habit", async () => {
    api.listHabits.mockResolvedValue([HABIT]);
    renderEdit();

    expect(await screen.findByLabelText("Name")).toHaveValue("Drink water");
    expect(screen.getByLabelText("Anchor")).toHaveValue("after coffee");
    expect(screen.getByLabelText("Cue time")).toHaveValue("08:30");
  });

  it("sends only the edited habit", async () => {
    api.listHabits.mockResolvedValue([HABIT]);
    api.updateHabit.mockResolvedValue({ ...HABIT, name: "Water" });
    renderEdit();
    const user = userEvent.setup();

    const nameInput = await screen.findByLabelText("Name");
    await user.clear(nameInput);
    await user.type(nameInput, "Water");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(api.updateHabit).toHaveBeenCalledTimes(1));
    const [id, payload] = api.updateHabit.mock.calls[0];
    expect(id).toBe(1);
    expect(payload.name).toBe("Water");
    expect(payload.anchor).toBe("after coffee"); // untouched field kept
  });

  it("surfaces API validation errors", async () => {
    api.listHabits.mockResolvedValue([HABIT]);
    api.updateHabit.mockRejectedValue(new Error("cue_time must be HH:MM"));
    renderEdit();
    const user = userEvent.setup();

    await screen.findByLabelText("Name");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText("cue_time must be HH:MM"),
    ).toBeInTheDocument();
  });

  it("reports an unknown habit", async () => {
    api.listHabits.mockResolvedValue([]);
    renderEdit();

    expect(await screen.findByText("Habit not found")).toBeInTheDocument();
    expect(api.updateHabit).not.toHaveBeenCalled();
  });
});
