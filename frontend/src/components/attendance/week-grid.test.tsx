import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarOut, DayOut } from "@/lib/api/types";

import { WeekGrid } from "./week-grid";

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-21",
    planned: "WORK",
    outcome: "OK",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    ...overrides,
  };
}

const calendar: CalendarOut = {
  start: "2026-09-21",
  end: "2026-09-22",
  employees: [{ id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" }],
  days: [
    day({ outcome: "LATE", checkin: "2026-09-21T16:51:00", minutes_late: 11 }),
    day({ day: "2026-09-22", outcome: "FUTURE" }),
  ],
  warnings: [],
};

describe("WeekGrid", () => {
  it("shows outcome text and check-in time per cell", () => {
    render(<WeekGrid calendar={calendar} onSelect={() => undefined} />);
    expect(screen.getByRole("columnheader", { name: "lun 21/09" })).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /EMPLEADO A/ });
    expect(row).toHaveTextContent("Retardo");
    expect(row).toHaveTextContent("16:51");
  });

  it("selects a day and disables future days", async () => {
    const onSelect = vi.fn();
    render(<WeekGrid calendar={calendar} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /lun 21\/09: Retardo 16:51/ }));
    expect(onSelect).toHaveBeenCalledWith(calendar.days[0], calendar.employees[0]);
    expect(screen.getByRole("button", { name: /mar 22\/09/ })).toBeDisabled();
  });
});
