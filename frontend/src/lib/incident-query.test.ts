import { describe, expect, it } from "vitest";

import {
  incidentQueryString,
  parseIncidentQuery,
  toApiParams,
  withFilters,
  type IncidentQuery,
} from "./incident-query";

const BASE: IncidentQuery = {
  from: "2026-09-01",
  to: "2026-09-30",
  employeeId: null,
  types: [],
  status: "all",
  page: 1,
  rhPage: 1,
};

describe("parseIncidentQuery", () => {
  it("needs a valid range", () => {
    expect(parseIncidentQuery({})).toBeNull();
    expect(parseIncidentQuery({ desde: "2026-09-01", hasta: "nope" })).toBeNull();
  });

  it("reads every filter and page", () => {
    const query = parseIncidentQuery({
      desde: "2026-09-01",
      hasta: "2026-09-30",
      empleado: "7",
      tipo: "LATE,ABSENT",
      estado: "unjustified",
      pag: "3",
      pag_rh: "2",
    });
    expect(query).toEqual({
      ...BASE,
      employeeId: 7,
      types: ["LATE", "ABSENT"],
      status: "unjustified",
      page: 3,
      rhPage: 2,
    });
  });

  it("ignores garbage and falls back to defaults", () => {
    const query = parseIncidentQuery({
      desde: "2026-09-01",
      hasta: "2026-09-30",
      empleado: "abc",
      tipo: "OK,FOO,LATE,LATE",
      estado: "toString",
      pag: "-3",
      pag_rh: "1.5",
    });
    expect(query).toEqual({ ...BASE, types: ["LATE"] });
  });

  it("uses the first value of repeated params", () => {
    const query = parseIncidentQuery({ desde: ["2026-09-01", "x"], hasta: "2026-09-30" });
    expect(query?.from).toBe("2026-09-01");
  });
});

describe("incidentQueryString", () => {
  it("omits defaults", () => {
    expect(incidentQueryString(BASE)).toBe("desde=2026-09-01&hasta=2026-09-30");
  });

  it("round-trips through parse", () => {
    const query = { ...BASE, employeeId: 7, types: ["LATE" as const], status: "justified" as const, page: 2, rhPage: 3 };
    const params = Object.fromEntries(new URLSearchParams(incidentQueryString(query)));
    expect(parseIncidentQuery(params)).toEqual(query);
  });
});

describe("withFilters", () => {
  it("resets both pages to 1", () => {
    const query = withFilters({ ...BASE, page: 4, rhPage: 2 }, { employeeId: 3 });
    expect(query).toEqual({ ...BASE, employeeId: 3 });
  });
});

describe("toApiParams", () => {
  it("only sends the filters that are set", () => {
    expect(toApiParams(BASE, 2)).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      status: "all",
      page: 2,
      limit: 25,
    });
    expect(toApiParams({ ...BASE, employeeId: 7, types: ["ABSENT"] }, 1, 100)).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      employee_id: 7,
      type: ["ABSENT"],
      status: "all",
      page: 1,
      limit: 100,
    });
  });
});
