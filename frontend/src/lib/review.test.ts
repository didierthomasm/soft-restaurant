import { describe, expect, it } from "vitest";

import type { FindingOut, NarrativeItemOut } from "@/lib/api/types";

import {
  actionHref,
  actionLabel,
  canApprove,
  defaultReviewMonday,
  describeFacts,
  formatDays,
  groupByPriority,
  isInProgress,
} from "./review";

const MONDAY = "2026-09-21";

function finding(overrides: Partial<FindingOut>): FindingOut {
  return {
    id: "ABSENT_NO_EXCEPTION:7:2026-09-23",
    kind: "ABSENT_NO_EXCEPTION",
    employee_id: 7,
    employee_name: "EMPLEADO G",
    days: ["2026-09-23"],
    facts: {},
    ...overrides,
  };
}

function item(findingId: string, overrides: Partial<NarrativeItemOut> = {}): NarrativeItemOut {
  return {
    finding_id: findingId,
    priority: "HIGH",
    explanation: "Revisar.",
    suggested_action: "JUSTIFY",
    ...overrides,
  };
}

describe("review helpers", () => {
  it("knows which statuses are in progress or approvable", () => {
    expect(isInProgress("QUEUED")).toBe(true);
    expect(isInProgress("READY")).toBe(false);
    expect(canApprove("READY_NO_NARRATIVE")).toBe(true);
    expect(canApprove("APPROVED")).toBe(false);
  });

  it("describes facts in Spanish", () => {
    expect(describeFacts(finding({ facts: { checkin_time: "16:45" } }))).toBe("checó 16:45");
    expect(
      describeFacts(finding({ facts: { late_this_week: 2, unjustified_this_week: 1, weeks_with_late: 3 } })),
    ).toBe("2 retardos esta semana · 1 sin justificar · 3 de las últimas 5 semanas con retardo");
    expect(describeFacts(finding({ facts: { code: "NO_REST_RULE", occurrences: 4 } }))).toBe(
      "Sin regla de descanso · 4 veces",
    );
  });

  it("formats day lists and long ranges", () => {
    expect(formatDays(["2026-09-23"])).toBe("23/09/2026");
    expect(formatDays(["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24"])).toBe(
      "21/09/2026 – 24/09/2026 (4 días)",
    );
  });

  it("groups findings by priority in order", () => {
    const high = finding({ id: "a" });
    const low = finding({ id: "b", kind: "CONFIG_WARNING" });
    const groups = groupByPriority([low, high], [item("b", { priority: "LOW" }), item("a")]);
    expect(groups.map((g) => [g.priority, g.entries.map((e) => e.finding.id)])).toEqual([
      ["HIGH", ["a"]],
      ["LOW", ["b"]],
    ]);
  });

  it("keeps every finding in one group when there is no narrative", () => {
    const groups = groupByPriority([finding({ id: "a" }), finding({ id: "b" })], null);
    expect(groups).toHaveLength(1);
    expect(groups[0].priority).toBeNull();
    expect(groups[0].entries.every((e) => e.item === null)).toBe(true);
  });

  it("links a finding to its day panel inside the reviewed week", () => {
    expect(actionHref(finding({}), MONDAY)).toBe(
      "/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    // Review Focus #1: a streak that began last week opens a day of this week.
    const streak = finding({ kind: "NO_CHECKIN_STREAK", days: ["2026-09-20", "2026-09-21"] });
    expect(actionHref(streak, MONDAY)).toBe("/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-21");
    expect(actionHref(finding({ kind: "CONFIG_WARNING", employee_id: null, days: [] }), MONDAY)).toBe(
      "/configuracion",
    );
    expect(actionHref(finding({ employee_id: null }), MONDAY)).toBeNull();
  });

  it("labels the action button", () => {
    expect(actionLabel(finding({}), item("x"))).toBe("Justificar");
    expect(actionLabel(finding({}), item("x", { suggested_action: "NONE" }))).toBe("Ver día");
    expect(actionLabel(finding({}), null)).toBe("Ver día");
    expect(actionLabel(finding({ kind: "CONFIG_WARNING" }), null)).toBe("Ir a configuración");
  });
});

describe("defaultReviewMonday", () => {
  it("uses the week of the newest draft", () => {
    expect(defaultReviewMonday({ year: 2026, week: 39 }, "2026-10-01")).toBe("2026-09-21");
    expect(defaultReviewMonday({ year: 2026, week: 53 }, "2026-10-01")).toBe("2026-12-28");
  });

  it("falls back to the current week without drafts", () => {
    expect(defaultReviewMonday(undefined, "2026-10-01")).toBe("2026-09-28");
  });
});
