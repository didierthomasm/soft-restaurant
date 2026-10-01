import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDeleteButton } from "./confirm-delete-button";

function setup() {
  const onConfirm = vi.fn();
  render(<ConfirmDeleteButton onConfirm={onConfirm} label="Eliminar regla de EMPLEADO A" />);
  return onConfirm;
}

describe("ConfirmDeleteButton", () => {
  it("does not delete on the first click", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar regla de EMPLEADO A" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Confirmar/ })).toBeInTheDocument();
  });

  it("deletes once on Confirmar", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar regla de EMPLEADO A" }));
    await userEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("returns to Eliminar on Cancelar without deleting", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar regla de EMPLEADO A" }));
    await userEvent.click(screen.getByRole("button", { name: /Cancelar/ }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Eliminar regla de EMPLEADO A" })).toBeInTheDocument();
  });
});
