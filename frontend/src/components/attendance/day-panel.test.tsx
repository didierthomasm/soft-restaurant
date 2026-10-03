import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DayOut, EmployeeRef } from "@/lib/api/types";

import { DayPanel } from "./day-panel";

const { mutation } = vi.hoisted(() => ({
  mutation: () => ({ mutate: vi.fn(), error: null, isPending: false }),
}));

vi.mock("@/lib/api/attendance", () => ({
  useCreateJustification: mutation,
  useUpdateJustification: mutation,
  useDeleteJustification: mutation,
  useRestSwap: mutation,
  useCreateException: mutation,
  useUpdateException: mutation,
  useDeleteException: mutation,
}));

const employee: EmployeeRef = { id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" };

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-30",
    planned: "WORK",
    outcome: "ABSENT",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
    ...overrides,
  };
}

describe("DayPanel", () => {
  it("edits the exception that justified the day instead of offering a new one", () => {
    const justified = day({
      planned: "ABSENCE",
      outcome: "JUSTIFIED",
      rh_type: "VACACIONES",
      comment: "Enfermedad.",
      exception: {
        id: 12,
        kind: "WORK_TO_ABSENCE",
        date_from: "2026-09-30",
        date_to: "2026-09-30",
        rh_type: "VACACIONES",
        comment: "Enfermedad.",
      },
    });
    render(<DayPanel selection={{ day: justified, employee }} onClose={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeInTheDocument();
    expect(screen.getByLabelText("Comentario")).toHaveValue("Enfermedad.");
    expect(screen.queryByRole("heading", { name: "Agregar excepción" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Cambio de descanso" })).not.toBeInTheDocument();
  });

  it("offers to justify and to add an exception on a plain absence", () => {
    render(<DayPanel selection={{ day: day({}), employee }} onClose={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Justificar falta" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agregar excepción" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cambio de descanso" })).toBeInTheDocument();
  });
});
