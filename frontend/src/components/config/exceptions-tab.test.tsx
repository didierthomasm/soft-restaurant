import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExceptionsTab } from "./exceptions-tab";

const { mutation } = vi.hoisted(() => ({
  mutation: () => ({ mutate: vi.fn(), error: null, isPending: false }),
}));

vi.mock("@/lib/api/attendance", () => ({
  useCreateException: mutation,
  useUpdateException: mutation,
  useDeleteException: mutation,
}));

vi.mock("@/lib/api/config", () => ({
  useEmployees: () => ({ data: [{ id: 1, short_name: "EMPLEADO A" }] }),
  useExceptions: () => ({
    isPending: false,
    isError: false,
    data: [
      {
        id: 5,
        kind: "WORK_TO_ABSENCE",
        employee_id: 1,
        date_from: "2026-09-30",
        date_to: "2026-09-30",
        rh_type: "VACACIONES",
        comment: "Viaje",
      },
    ],
  }),
}));

describe("ExceptionsTab", () => {
  it("opens the exception in an edit dialog", async () => {
    render(<ExceptionsTab />);
    await userEvent.click(screen.getByRole("button", { name: "Editar Ausencia justificada del 30/09/2026" }));
    const dialog = screen.getByRole("dialog", { name: "Editar excepción" });
    expect(dialog).toHaveTextContent("EMPLEADO A");
    expect(screen.getByLabelText("Comentario")).toHaveValue("Viaje");
  });
});
