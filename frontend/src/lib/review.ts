import type {
  FindingKind,
  FindingOut,
  NarrativeItemOut,
  Priority,
  ReviewStatus,
  ReviewTrigger,
  SuggestedAction,
  WarningCode,
} from "@/lib/api/types";

import { formatDate, isoWeekMonday, weekStart } from "./dates";
import { WARNING_LABELS } from "./labels";

export const FINDING_LABELS: Record<FindingKind, string> = {
  REST_DAY_CHECKIN: "Checada en día de descanso",
  ABSENT_NO_EXCEPTION: "Falta sin justificar",
  NO_CHECKIN_STREAK: "Varios días sin checar",
  REPEATED_LATE: "Retardos repetidos",
  CONFIG_WARNING: "Aviso de configuración",
};

export const PRIORITY_LABELS: Record<Priority, string> = { HIGH: "Alta", MEDIUM: "Media", LOW: "Baja" };
export const PRIORITY_ORDER: Priority[] = ["HIGH", "MEDIUM", "LOW"];

export const ACTION_LABELS: Record<SuggestedAction, string> = {
  JUSTIFY: "Justificar",
  REST_SWAP: "Registrar cambio de descanso",
  ADD_EXCEPTION: "Registrar excepción",
  FIX_CONFIG: "Corregir configuración",
  NONE: "",
};

export const STATUS_LABELS: Record<ReviewStatus, string> = {
  QUEUED: "En cola",
  RUNNING: "Generando",
  READY: "Listo",
  READY_NO_NARRATIVE: "Listo sin redacción",
  FAILED: "Falló",
  APPROVED: "Aprobado",
};

export const TRIGGER_LABELS: Record<ReviewTrigger, string> = {
  THURSDAY: "Jueves",
  MONDAY: "Lunes",
  MANUAL: "Manual",
};

export function isInProgress(status: ReviewStatus): boolean {
  return status === "QUEUED" || status === "RUNNING";
}

export function canApprove(status: ReviewStatus): boolean {
  return status === "READY" || status === "READY_NO_NARRATIVE";
}

const FACTS: Record<string, (value: number | string) => string> = {
  checkin_time: (v) => `checó ${v}`,
  days: (v) => `${v} días`,
  late_this_week: (v) => `${v} retardos esta semana`,
  unjustified_this_week: (v) => `${v} sin justificar`,
  weeks_with_late: (v) => `${v} de las últimas 5 semanas con retardo`,
  occurrences: (v) => `${v} veces`,
};

export function describeFacts(finding: FindingOut): string {
  const code = finding.facts.code;
  const warning = typeof code === "string" && code in WARNING_LABELS ? [WARNING_LABELS[code as WarningCode]] : [];
  const described = Object.entries(finding.facts)
    .filter(([key]) => key in FACTS)
    .map(([key, value]) => FACTS[key](value));
  return [...warning, ...described].join(" · ");
}

export function formatDays(days: string[]): string {
  if (days.length <= 3) return days.map(formatDate).join(", ");
  return `${formatDate(days[0])} – ${formatDate(days[days.length - 1])} (${days.length} días)`;
}

export type ReviewEntry = { finding: FindingOut; item: NarrativeItemOut | null };
export type ReviewGroup = { priority: Priority | null; entries: ReviewEntry[] };

export function groupByPriority(findings: FindingOut[], items: NarrativeItemOut[] | null): ReviewGroup[] {
  if (items === null) {
    return [{ priority: null, entries: findings.map((finding) => ({ finding, item: null })) }];
  }
  const byId = new Map(items.map((entry) => [entry.finding_id, entry]));
  return PRIORITY_ORDER.map((priority) => ({
    priority,
    entries: findings
      .filter((finding) => byId.get(finding.id)?.priority === priority)
      .map((finding) => ({ finding, item: byId.get(finding.id) ?? null })),
  })).filter((group) => group.entries.length > 0);
}

export function actionHref(finding: FindingOut, weekMonday: string): string | null {
  if (finding.kind === "CONFIG_WARNING") return "/configuracion";
  if (finding.employee_id === null || finding.days.length === 0) return null;
  const day = finding.days.find((d) => d >= weekMonday) ?? finding.days[finding.days.length - 1];
  return `/semana?desde=${weekMonday}&empleado=${finding.employee_id}&dia=${day}`;
}

export function actionLabel(finding: FindingOut, item: NarrativeItemOut | null): string {
  const suggested = item ? ACTION_LABELS[item.suggested_action] : "";
  if (suggested) return suggested;
  return finding.kind === "CONFIG_WARNING" ? "Ir a configuración" : "Ver día";
}

/** Monday shown by /revision without ?desde: the week of the newest draft, else this week. */
export function defaultReviewMonday(latest: { year: number; week: number } | undefined, today: string): string {
  return latest ? isoWeekMonday(latest.year, latest.week) : weekStart(today);
}
