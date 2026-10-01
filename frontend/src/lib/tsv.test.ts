import { describe, expect, it } from "vitest";

import type { RhRowOut } from "@/lib/api/types";

import { rhRowsToTsv } from "./tsv";

const row = (overrides: Partial<RhRowOut>): RhRowOut => ({
  employee_id: 1,
  name: "APELLIDO UNO",
  day: "2026-09-23",
  rh_type: "RETARDO",
  comment: "",
  ...overrides,
});

describe("rhRowsToTsv", () => {
  it("renders a header and one line per row with Spanish labels", () => {
    expect(rhRowsToTsv([row({}), row({ day: "2026-09-24", rh_type: "VACACIONES" })])).toBe(
      [
        "Nombre\tFecha\tTipo\tComentario",
        "APELLIDO UNO\t23/09/2026\tRetardo\t",
        "APELLIDO UNO\t24/09/2026\tVacaciones\t",
      ].join("\n"),
    );
  });

  it("keeps columns intact when comments contain tabs or newlines", () => {
    const tsv = rhRowsToTsv([row({ comment: "cita\tmédica\nIMSS" })]);
    expect(tsv.split("\n")[1]).toBe("APELLIDO UNO\t23/09/2026\tRetardo\tcita médica IMSS");
  });
});
