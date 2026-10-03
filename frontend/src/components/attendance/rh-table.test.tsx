import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RhTable } from "./rh-table";

const rows = [
  { employee_id: 1, name: "APELLIDO UNO", day: "2026-09-23", rh_type: "RETARDO" as const, comment: "" },
];

describe("RhTable", () => {
  it("lists rows with Spanish labels", () => {
    render(<RhTable rows={rows} />);
    const row = screen.getByRole("row", { name: /APELLIDO UNO/ });
    expect(row).toHaveTextContent("23/09/2026");
    expect(row).toHaveTextContent("Retardo");
  });

  it("copies the list as TSV", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<RhTable rows={rows} />);
    await user.click(screen.getByRole("button", { name: "Copiar para RH" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("APELLIDO UNO\t23/09/2026"));
  });

  it("says when there is nothing to capture", () => {
    render(<RhTable rows={[]} />);
    expect(screen.getByText("Sin incidencias para capturar en RH.")).toBeInTheDocument();
  });

  it("copies every row from loadAll, not only the visible page", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    const second = { ...rows[0], name: "APELLIDO DOS", day: "2026-09-24" };
    render(<RhTable rows={rows} loadAll={async () => [...rows, second]} />);
    await user.click(screen.getByRole("button", { name: "Copiar para RH" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("APELLIDO DOS\t24/09/2026"));
    expect(screen.getByText("Copia todas las filas del filtro, no solo esta página.")).toBeInTheDocument();
  });
});
