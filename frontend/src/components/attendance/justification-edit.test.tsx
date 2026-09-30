import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { JustificationEdit } from "./justification-edit";

const update = vi.fn();
const remove = vi.fn();

vi.mock("@/lib/api/attendance", () => ({
  useUpdateJustification: () => ({ mutate: update, error: null, isPending: false }),
  useDeleteJustification: () => ({ mutate: remove, error: null, isPending: false }),
}));

function setup(incident: "LATE" | "ABSENT" = "ABSENT") {
  const onDone = vi.fn();
  render(
    <JustificationEdit
      justificationId={42}
      incident={incident}
      rhType="VACACIONES"
      reason="Viaje familiar"
      onDone={onDone}
    />,
  );
  return onDone;
}

describe("JustificationEdit", () => {
  beforeEach(() => {
    update.mockReset();
    remove.mockReset();
  });

  it("shows the current RH type and reason", () => {
    setup();
    expect(screen.getByText("Vacaciones · Viaje familiar")).toBeInTheDocument();
  });

  it("deletes the justification by id after confirming", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar justificación" }));
    expect(remove).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(remove).toHaveBeenCalledWith(42, expect.anything());
  });

  it("changes the RH type with the allowed options for the incident", async () => {
    setup();
    await userEvent.selectOptions(screen.getByLabelText("Tipo en RH"), "INCAPACIDAD");
    await userEvent.click(screen.getByRole("button", { name: "Cambiar tipo en RH" }));
    expect(update).toHaveBeenCalledWith(
      { id: 42, body: { rh_type: "INCAPACIDAD" } },
      expect.anything(),
    );
  });

  it("only offers late types for a late incident", () => {
    setup("LATE");
    const options = screen.getAllByRole("option").map((o) => o.getAttribute("value"));
    expect(options).toEqual(["NO_CAPTURAR", "RETARDO"]);
  });
});
