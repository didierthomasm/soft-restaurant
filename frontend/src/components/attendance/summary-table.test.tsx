import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SummaryOut } from "@/lib/api/types";

import { SummaryTable } from "./summary-table";

const summary: SummaryOut = {
  employee_id: 1,
  period: "2026-09",
  worked: 20,
  late: 3,
  late_justified: 1,
  absent: 2,
  absent_justified: 1,
  justified_by_type: { VACACIONES: 2 },
  unresolved: 1,
};

describe("SummaryTable", () => {
  it("shows totals with justified counts and absence types", () => {
    render(<SummaryTable summaries={[summary]} names={new Map([[1, "EMPLEADO A"]])} />);
    const row = screen.getByRole("row", { name: /EMPLEADO A/ });
    expect(row).toHaveTextContent("20");
    expect(row).toHaveTextContent("3 (1 just.)");
    expect(row).toHaveTextContent("2 (1 just.)");
    expect(row).toHaveTextContent("Vacaciones: 2");
  });
});
