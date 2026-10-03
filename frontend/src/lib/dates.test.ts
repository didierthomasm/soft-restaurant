import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  formatDate,
  formatDateTime,
  formatDay,
  formatMonth,
  formatTime,
  isIsoDate,
  isIsoMonth,
  isWeekend,
  isoWeekMonday,
  isoWeekNumber,
  isoWeekYear,
  monthRange,
  todayIso,
  weekStart,
} from "./dates";

describe("dates", () => {
  it("finds the Monday of the week", () => {
    expect(weekStart("2026-09-27")).toBe("2026-09-21");
    expect(weekStart("2026-09-21")).toBe("2026-09-21");
  });

  it("adds days across months and years", () => {
    expect(addDays("2026-09-30", 1)).toBe("2026-10-01");
    expect(addDays("2027-01-01", -1)).toBe("2026-12-31");
  });

  it("builds month ranges", () => {
    expect(monthRange("2026-02-15")).toEqual({ from: "2026-02-01", to: "2026-02-28" });
  });

  it("lists days inclusively", () => {
    expect(daysBetween("2026-09-29", "2026-10-01")).toEqual([
      "2026-09-29",
      "2026-09-30",
      "2026-10-01",
    ]);
  });

  it("computes ISO week numbers at year boundaries", () => {
    expect(isoWeekNumber("2026-09-23")).toBe(39);
    expect(isoWeekNumber("2027-01-01")).toBe(53);
    expect(isoWeekNumber("2026-01-01")).toBe(1);
  });

  it("validates ISO dates", () => {
    expect(isIsoDate("2026-09-21")).toBe(true);
    expect(isIsoDate("2026-02-30")).toBe(false);
    expect(isIsoDate("21/09/2026")).toBe(false);
    expect(isIsoDate(undefined)).toBe(false);
  });

  it("uses local time for today", () => {
    expect(todayIso(new Date(2026, 8, 27, 23, 30))).toBe("2026-09-27");
  });

  it("formats for display", () => {
    expect(formatDay("2026-09-23")).toBe("mié 23/09");
    expect(formatDate("2026-09-23")).toBe("23/09/2026");
    expect(formatTime("2026-09-23T16:51:07")).toBe("16:51");
    expect(formatTime(null)).toBe("");
  });

  it("finds the ISO week-numbering year", () => {
    expect(isoWeekYear("2026-09-21")).toBe(2026);
    expect(isoWeekYear("2026-12-28")).toBe(2026); // W53
    expect(isoWeekYear("2027-01-01")).toBe(2026); // still 2026-W53
    expect(isoWeekYear("2027-01-04")).toBe(2027);
  });

  it("finds the Monday of an ISO week", () => {
    expect(isoWeekMonday(2026, 39)).toBe("2026-09-21");
    expect(isoWeekMonday(2026, 53)).toBe("2026-12-28");
    expect(isoWeekMonday(2027, 1)).toBe("2027-01-04");
  });

  it("formats naive backend datetimes", () => {
    expect(formatDateTime("2026-09-24T17:30:00")).toBe("24/09/2026 17:30");
    expect(formatDateTime(null)).toBe("");
  });
});

describe("month helpers", () => {
  it("validates YYYY-MM", () => {
    expect(isIsoMonth("2026-09")).toBe(true);
    expect(isIsoMonth("2026-13")).toBe(false);
    expect(isIsoMonth("2026-9")).toBe(false);
    expect(isIsoMonth(undefined)).toBe(false);
  });

  it("formats a month in Spanish", () => {
    expect(formatMonth("2026-09")).toBe("septiembre 2026");
  });

  it("detects weekends", () => {
    expect(isWeekend("2026-09-26")).toBe(true); // Saturday
    expect(isWeekend("2026-09-27")).toBe(true); // Sunday
    expect(isWeekend("2026-09-28")).toBe(false); // Monday
  });
});
