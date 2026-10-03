import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { IncidentQuery } from "@/lib/incident-query";

import { IncidentFilters } from "./incident-filters";

const QUERY: IncidentQuery = {
  from: "2026-09-01",
  to: "2026-09-30",
  employeeId: null,
  types: [],
  status: "all",
  page: 3,
  rhPage: 2,
};
const employees = [
  { id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" as const },
  { id: 2, short_name: "EMPLEADO B", rh_name: null, area: "KITCHEN" as const },
];

describe("IncidentFilters", () => {
  it("applies employee, types and status and goes back to page 1", async () => {
    const onApply = vi.fn();
    render(<IncidentFilters query={QUERY} employees={employees} onApply={onApply} />);
    await userEvent.selectOptions(screen.getByLabelText("Empleado"), "2");
    await userEvent.click(screen.getByLabelText("Retardo"));
    await userEvent.click(screen.getByLabelText("Falta"));
    await userEvent.selectOptions(screen.getByLabelText("Estado"), "unjustified");
    await userEvent.click(screen.getByRole("button", { name: "Ver" }));
    expect(onApply).toHaveBeenCalledWith({
      ...QUERY,
      employeeId: 2,
      types: ["LATE", "ABSENT"],
      status: "unjustified",
      page: 1,
      rhPage: 1,
    });
  });

  it("clears the filters but keeps the range", async () => {
    const onApply = vi.fn();
    const filtered = { ...QUERY, employeeId: 1, types: ["LATE" as const], status: "justified" as const };
    render(<IncidentFilters query={filtered} employees={employees} onApply={onApply} />);
    expect(screen.getByLabelText("Retardo")).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));
    expect(onApply).toHaveBeenCalledWith({ ...QUERY, page: 1, rhPage: 1 });
  });

  it("selects the employee from the URL once the employee list arrives", () => {
    const filtered = { ...QUERY, employeeId: 2 };
    const { rerender } = render(<IncidentFilters query={filtered} employees={[]} onApply={() => undefined} />);
    rerender(<IncidentFilters query={filtered} employees={employees} onApply={() => undefined} />);
    expect(screen.getByLabelText("Empleado")).toHaveValue("2");
  });
});
