import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import NewHabit from "../pages/NewHabit";

vi.mock("../api", () => ({
  api: { createHabit: vi.fn() },
  localDate: () => "2026-09-30",
}));

const { api } = await import("../api");

beforeEach(() => {
  vi.clearAllMocks();
  api.createHabit.mockResolvedValue({ id: 1, if_then: "…" });
});

describe("NewHabit wizard", () => {
  it("keeps Next disabled until the name and the anchor are filled", async () => {
    render(
      <MemoryRouter>
        <NewHabit />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    const next = screen.getByRole("button", { name: "Next" });
    expect(next).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/Short name/), "Drink water");
    expect(next).toBeDisabled(); // anchor still empty

    await user.type(
      screen.getByPlaceholderText(/pour my morning coffee/),
      "after coffee",
    );
    expect(next).toBeEnabled();
  });

  it("creates the habit with a name distinct from the behavior", async () => {
    render(
      <MemoryRouter>
        <NewHabit />
      </MemoryRouter>,
    );
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText(/Short name/), "Drink water");
    await user.type(
      screen.getByPlaceholderText(/pour my morning coffee/),
      "after coffee",
    );
    await user.click(screen.getByRole("button", { name: "Next" }));

    await user.type(
      screen.getByPlaceholderText(/do 2 push-ups/),
      "drink one glass",
    );
    await user.click(screen.getByRole("button", { name: "Next" }));

    await user.type(
      screen.getByPlaceholderText(/smile and say yes/),
      "smile",
    );
    await user.click(screen.getByRole("button", { name: "Create Habit" }));

    await waitFor(() => expect(api.createHabit).toHaveBeenCalledTimes(1));
    const payload = api.createHabit.mock.calls[0][0];
    expect(payload.name).toBe("Drink water");
    expect(payload.tiny_behavior).toBe("drink one glass");
    expect(payload.anchor).toBe("after coffee");
    expect(payload.celebration).toBe("smile");
  });
});
