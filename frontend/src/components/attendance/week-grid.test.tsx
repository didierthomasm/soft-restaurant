import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarOut, DayOut } from "@/lib/api/types";

import { findDaySelection, WeekGrid } from "./week-grid";

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
    exception: null,
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
  it("marks days changed by an exception", () => {
    const present = {
      ...calendar,
      days: [
        day({
          exception: {
            id: 3,
            kind: "PRESENT_NO_CHECKIN",
            date_from: "2026-09-21",
            date_to: "2026-09-21",
            rh_type: null,
            comment: "",
          },
        }),
      ],
    };
    render(<WeekGrid calendar={present} onSelect={() => undefined} />);
    expect(screen.getByRole("button", { name: /lun 21\/09: A tiempo \(excepción\)/ })).toHaveTextContent(
      "Excepción",
    );
  });
});

describe("findDaySelection", () => {
  it("finds the employee and day of a deep link", () => {
    expect(findDaySelection(calendar, 1, "2026-09-21")).toEqual({
      day: calendar.days[0],
      employee: calendar.employees[0],
    });
  });

  it("ignores unknown employees and days outside the calendar", () => {
    expect(findDaySelection(calendar, 99, "2026-09-21")).toBeNull();
    expect(findDaySelection(calendar, 1, "2026-10-05")).toBeNull();
  });
});
