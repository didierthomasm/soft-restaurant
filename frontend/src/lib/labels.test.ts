import { describe, expect, it } from "vitest";

import { INCIDENT_TYPES, JUSTIFICATION_RH_TYPES, STATUS_LABELS, incidentFor } from "./labels";

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
