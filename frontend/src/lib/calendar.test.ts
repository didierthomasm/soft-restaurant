import { describe, expect, it } from "vitest";

import {
  legacySummaryHref,
  legacyWeekHref,
  monthHref,
  parseFocus,
  summaryHref,
  weekHref,
} from "./calendar";

describe("calendar hrefs", () => {
  it("builds week, month and summary links", () => {
    expect(weekHref("2026-09-21")).toBe("/calendario?vista=semana&desde=2026-09-21");
    expect(weekHref("2026-09-21", { employeeId: 7, day: "2026-09-23" })).toBe(
      "/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    expect(monthHref("2026-09")).toBe("/calendario?vista=mes&mes=2026-09");
    expect(summaryHref("2026-09")).toBe("/resumen?mes=2026-09");
  });

  it("parses a deep-link focus", () => {
    expect(parseFocus("7", "2026-09-23")).toEqual({ employeeId: 7, day: "2026-09-23" });
    expect(parseFocus("0", "2026-09-23")).toBeNull();
    expect(parseFocus("7", "ayer")).toBeNull();
    expect(parseFocus(undefined, undefined)).toBeNull();
  });
});

describe("legacy redirects", () => {
  it("keeps the week and the focused day", () => {
    expect(legacyWeekHref({ desde: "2026-09-21", empleado: "7", dia: "2026-09-23" })).toBe(
      "/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    expect(legacyWeekHref({})).toBe("/calendario?vista=semana");
  });

  it("drops invalid values", () => {
    expect(legacyWeekHref({ desde: "x", empleado: "7", dia: "y" })).toBe("/calendario?vista=semana");
  });

  it("sends the month summary to /resumen", () => {
    expect(legacySummaryHref({ mes: "2026-09" })).toBe("/resumen?mes=2026-09");
    expect(legacySummaryHref({ mes: "2026-13" })).toBe("/resumen");
    expect(legacySummaryHref({})).toBe("/resumen");
  });
});
