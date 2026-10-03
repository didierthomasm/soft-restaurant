import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarOut, DayOut } from "@/lib/api/types";

import { MonthGrid } from "./month-grid";

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-25",
    planned: "WORK",
    outcome: "OK",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
    ...overrides,
  };
}

const calendar: CalendarOut = {
  start: "2026-09-25",
  end: "2026-09-27",
  employees: [{ id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" }],
  days: [
    day({ outcome: "LATE", checkin: "2026-09-25T16:55:00", minutes_late: 15 }),
    day({ day: "2026-09-26", outcome: "REST", planned: "REST" }),
    day({ day: "2026-09-27", outcome: "FUTURE" }),
  ],
  warnings: [],
};

describe("MonthGrid", () => {
  it("shows one compact cell per day with the details in its label", () => {
    render(<MonthGrid calendar={calendar} onSelect={() => undefined} />);
    expect(screen.getByRole("columnheader", { name: "vie 25/09" })).toHaveTextContent("25");
    const late = screen.getByRole("button", { name: "vie 25/09: Retardo 16:55" });
    expect(late).toHaveTextContent("R");
    expect(late).toHaveAttribute("title", "vie 25/09: Retardo 16:55");
    expect(screen.getByRole("button", { name: /sáb 26\/09: Descanso/ })).toHaveTextContent("D");
  });

  it("selects a day and disables future days", async () => {
    const onSelect = vi.fn();
    render(<MonthGrid calendar={calendar} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /vie 25\/09/ }));
    expect(onSelect).toHaveBeenCalledWith(calendar.days[0], calendar.employees[0]);
    expect(screen.getByRole("button", { name: /dom 27\/09/ })).toBeDisabled();
  });
});
