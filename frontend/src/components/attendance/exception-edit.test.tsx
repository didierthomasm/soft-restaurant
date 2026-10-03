import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExceptionRef } from "@/lib/api/types";

import { ExceptionEdit } from "./exception-edit";

const update = vi.fn();
const remove = vi.fn();

vi.mock("@/lib/api/attendance", () => ({
  useUpdateException: () => ({ mutate: update, error: null, isPending: false }),
  useDeleteException: () => ({ mutate: remove, error: null, isPending: false }),
}));

const VACATION: ExceptionRef = {
  id: 12,
  kind: "WORK_TO_ABSENCE",
  date_from: "2026-09-30",
  date_to: "2026-10-02",
  rh_type: "VACACIONES",
  comment: "Enfermedad.",
};

describe("ExceptionEdit", () => {
  beforeEach(() => {
    update.mockReset();
    remove.mockReset();
  });

  it("shows the existing exception filled in", () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeInTheDocument();
    expect(screen.getByText(/Aplica del 30\/09\/2026 al 02\/10\/2026/)).toBeInTheDocument();
    expect(screen.getByLabelText("Tipo en RH")).toHaveValue("VACACIONES");
    expect(screen.getByLabelText("Comentario")).toHaveValue("Enfermedad.");
    expect(screen.getByLabelText("Desde")).toHaveValue("2026-09-30");
    expect(screen.getByLabelText("Hasta")).toHaveValue("2026-10-02");
  });

  it("saves the edited fields", async () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    await userEvent.selectOptions(screen.getByLabelText("Tipo en RH"), "INCAPACIDAD");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(update).toHaveBeenCalledWith(
      {
        id: 12,
        body: {
          date_from: "2026-09-30",
          date_to: "2026-10-02",
          comment: "Enfermedad.",
          rh_type: "INCAPACIDAD",
        },
      },
      expect.anything(),
    );
  });

  it("does not offer an RH type for non-absence exceptions", async () => {
    const present = { ...VACATION, kind: "PRESENT_NO_CHECKIN" as const, rh_type: null, date_to: "2026-09-30" };
    render(<ExceptionEdit exception={present} onDone={() => undefined} />);
    expect(screen.queryByLabelText("Tipo en RH")).not.toBeInTheDocument();
    expect(screen.queryByText(/Aplica del/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(update.mock.calls[0][0].body).not.toHaveProperty("rh_type");
  });

  it("deletes after confirming", async () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    await userEvent.click(screen.getByRole("button", { name: "Eliminar excepción" }));
    await userEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(remove).toHaveBeenCalledWith(12, expect.anything());
  });
});
