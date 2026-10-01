import { describe, expect, it } from "vitest";

import { JUSTIFICATION_RH_TYPES, incidentFor } from "./labels";

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
