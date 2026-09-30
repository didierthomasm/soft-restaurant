import type { ExceptionKind, Incident, Outcome, RhType, WarningCode } from "@/lib/api/types";

export const OUTCOME_LABELS: Record<Outcome, string> = {
  OK: "A tiempo",
  LATE: "Retardo",
  ABSENT: "Falta",
  UNREGISTERED_CHANGE: "Cambio sin registrar",
  REST: "Descanso",
  CLOSED: "Cerrado",
  JUSTIFIED: "Justificado",
  PENDING: "Pendiente",
  FUTURE: "",
};

export const OUTCOME_STYLES: Record<Outcome, string> = {
  OK: "bg-emerald-50 text-emerald-900",
  LATE: "bg-amber-100 text-amber-950",
  ABSENT: "bg-red-100 text-red-950",
  UNREGISTERED_CHANGE: "bg-violet-100 text-violet-950",
  REST: "bg-muted text-muted-foreground",
  CLOSED: "bg-zinc-200 text-zinc-800",
  JUSTIFIED: "bg-sky-100 text-sky-950",
  PENDING: "border border-dashed text-muted-foreground",
  FUTURE: "text-muted-foreground",
};

export const RH_LABELS: Record<RhType, string> = {
  RETARDO: "Retardo",
  FALTA_INJUSTIFICADA: "Falta injustificada",
  FALTA_JUSTIFICADA: "Falta justificada",
  VACACIONES: "Vacaciones",
  INCAPACIDAD: "Incapacidad",
  PERMISO: "Permiso",
  DESCANSO: "Descanso",
  NO_CAPTURAR: "No se captura",
};

export const EXCEPTION_KIND_LABELS: Record<ExceptionKind, string> = {
  STORE_CLOSED: "Cierre del local",
  PRESENT_NO_CHECKIN: "Asistió sin checada",
  REST_TO_WORK: "Descanso → laboral",
  WORK_TO_ABSENCE: "Ausencia justificada",
  MANUAL_ABSENCE: "Falta registrada a mano",
};

// NO_SR_ID exists in the backend source but not yet in the committed schema.d.ts (the running
// backend image predates it). Drop the extra union member after the next `npm run gen:api`.
export const WARNING_LABELS: Record<WarningCode | "NO_SR_ID", string> = {
  NO_REST_RULE: "Sin regla de descanso",
  UNMAPPED_CHECKIN: "Checada sin empleado",
  ORPHAN_JUSTIFICATION: "Justificación sin incidencia",
  MISSING_RH_NAME: "Falta nombre en RH",
  NO_SR_ID: "Sin id de SR",
};

/** Index = backend weekday (0 = Monday … 6 = Sunday). */
export const WEEKDAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

export const ABSENCE_RH_TYPES: RhType[] = [
  "FALTA_JUSTIFICADA",
  "VACACIONES",
  "INCAPACIDAD",
  "PERMISO",
  "DESCANSO",
];

/** First option = backend default. */
export const JUSTIFICATION_RH_TYPES: Record<Incident, RhType[]> = {
  LATE: ["NO_CAPTURAR", "RETARDO"],
  ABSENT: [...ABSENCE_RH_TYPES, "NO_CAPTURAR"],
};

export function incidentFor(outcome: Outcome): Incident | null {
  if (outcome === "LATE") return "LATE";
  if (outcome === "ABSENT") return "ABSENT";
  return null;
}
