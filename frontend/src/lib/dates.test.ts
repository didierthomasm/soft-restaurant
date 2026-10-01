import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  formatDate,
  formatDay,
  formatTime,
  isIsoDate,
  isoWeekNumber,
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
});
