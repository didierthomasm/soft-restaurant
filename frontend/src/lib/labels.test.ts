import { describe, expect, it } from "vitest";

import type { DayOut } from "@/lib/api/types";

import {
  INCIDENT_TYPES,
  JUSTIFICATION_RH_TYPES,
  OUTCOME_SHORT,
  OUTCOME_STYLES,
  STATUS_LABELS,
  dayStyle,
  incidentAction,
  incidentFor,
} from "./labels";

describe("labels", () => {
  it("maps outcomes to justifiable incidents", () => {
    expect(incidentFor("LATE")).toBe("LATE");
    expect(incidentFor("ABSENT")).toBe("ABSENT");
    expect(incidentFor("UNREGISTERED_CHANGE")).toBeNull();
    expect(incidentFor("OK")).toBeNull();
  });

  it("defaults justifications like the backend", () => {
    expect(JUSTIFICATION_RH_TYPES.LATE[0]).toBe("NO_CAPTURAR");
    expect(JUSTIFICATION_RH_TYPES.ABSENT[0]).toBe("FALTA_JUSTIFICADA");
  });
});

describe("incident filter labels", () => {
  it("lists the four incident types in display order", () => {
    expect(INCIDENT_TYPES).toEqual(["LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED"]);
  });

  it("labels every status", () => {
    expect(STATUS_LABELS).toEqual({
      all: "Todas",
      justified: "Justificadas",
      unjustified: "Sin justificar",
    });
  });
});

describe("incidentAction", () => {
  const base: DayOut = {
    employee_id: 1,
    day: "2026-09-23",
    planned: "WORK",
    outcome: "LATE",
    checkin: null,
    minutes_late: 5,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
  };

  it("offers the right action per incident", () => {
    expect(incidentAction(base)).toBe("Justificar");
    expect(incidentAction({ ...base, justification_id: 4 })).toBe("Editar");
    expect(incidentAction({ ...base, outcome: "JUSTIFIED", planned: "ABSENCE" })).toBe("Editar");
    expect(incidentAction({ ...base, outcome: "UNREGISTERED_CHANGE", planned: "REST" })).toBe("Resolver");
    expect(incidentAction({ ...base, outcome: "OK" })).toBeNull();
  });
});

describe("OUTCOME_SHORT", () => {
  it("abbreviates every visible outcome with a distinct letter", () => {
    const shown = ["OK", "LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED", "REST", "CLOSED"] as const;
    const letters = shown.map((outcome) => OUTCOME_SHORT[outcome]);
    expect(letters).toEqual(["A", "R", "F", "C", "J", "D", "X"]);
    expect(new Set(letters).size).toBe(letters.length);
  });
});

describe("dayStyle", () => {
  const day = (outcome: "LATE" | "ABSENT", justification_id: number | null) => ({
    outcome,
    justification_id,
  });

  it("paints justified lates and absences green, like an on-time day", () => {
    expect(dayStyle(day("LATE", 4))).toBe(OUTCOME_STYLES.OK);
    expect(dayStyle(day("ABSENT", 4))).toBe(OUTCOME_STYLES.OK);
  });

  it("keeps the outcome color when nothing is justified", () => {
    expect(dayStyle(day("LATE", null))).toBe(OUTCOME_STYLES.LATE);
    expect(dayStyle(day("ABSENT", null))).toBe(OUTCOME_STYLES.ABSENT);
  });
});
