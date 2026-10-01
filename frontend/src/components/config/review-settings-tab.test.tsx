import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewSettingsTab } from "./review-settings-tab";

const save = vi.fn();

vi.mock("@/lib/api/reviews", () => ({
  useReviewSettings: () => ({
    data: { streak_days: 2, late_week: 2, late_weeks: 3 },
    isPending: false,
    isError: false,
  }),
  useSaveReviewSettings: () => ({ mutate: save, error: null, isPending: false }),
}));

describe("ReviewSettingsTab", () => {
  it("shows the current thresholds and saves new ones", async () => {
    render(<ReviewSettingsTab />);
    const streak = screen.getByLabelText(/Días seguidos sin checar/);
    expect(streak).toHaveValue(2);
    expect(screen.getByLabelText(/Semanas con retardo/)).toHaveAttribute("max", "5");
    await userEvent.clear(streak);
    await userEvent.type(streak, "3");
    await userEvent.click(screen.getByRole("button", { name: "Guardar umbrales" }));
    expect(save).toHaveBeenCalledWith(
      { streak_days: 3, late_week: 2, late_weeks: 3 },
      expect.anything(),
    );
  });
});
