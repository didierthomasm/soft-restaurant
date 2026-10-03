import { describe, expect, it } from "vitest";

import type { DayOut } from "@/lib/api/types";

import { INCIDENT_TYPES, JUSTIFICATION_RH_TYPES, STATUS_LABELS, incidentAction, incidentFor } from "./labels";

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
