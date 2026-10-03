import { isIsoDate, isIsoMonth } from "./dates";

export type DayFocus = { employeeId: number; day: string };

export function parseFocus(empleado: string | undefined, dia: string | undefined): DayFocus | null {
  const employeeId = Number(empleado);
  if (!Number.isInteger(employeeId) || employeeId <= 0 || !isIsoDate(dia)) return null;
  return { employeeId, day: dia };
}

export function weekHref(start: string, focus: DayFocus | null = null): string {
  const params = new URLSearchParams({ vista: "semana", desde: start });
  if (focus) {
    params.set("empleado", String(focus.employeeId));
    params.set("dia", focus.day);
  }
  return `/calendario?${params}`;
}

export function monthHref(month: string): string {
  return `/calendario?vista=mes&mes=${month}`;
}

export function summaryHref(month: string): string {
  return `/resumen?mes=${month}`;
}

export function legacyWeekHref(params: { desde?: string; empleado?: string; dia?: string }): string {
  if (!isIsoDate(params.desde)) return "/calendario?vista=semana";
  return weekHref(params.desde, parseFocus(params.empleado, params.dia));
}

export function legacySummaryHref(params: { mes?: string }): string {
  return isIsoMonth(params.mes) ? summaryHref(params.mes) : "/resumen";
}
