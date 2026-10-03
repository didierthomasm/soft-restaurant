import type { IncidentApiParams } from "@/lib/api/attendance";
import type { IncidentStatus, IncidentType } from "@/lib/api/types";

import { isIsoDate } from "./dates";
import { INCIDENT_TYPES, STATUS_LABELS } from "./labels";

export const PAGE_SIZE = 25;
export const COPY_PAGE_SIZE = 100;

export type IncidentQuery = {
  from: string;
  to: string;
  employeeId: number | null;
  types: IncidentType[];
  status: IncidentStatus;
  page: number;
  rhPage: number;
};

export type UrlParams = Record<string, string | string[] | undefined>;
type FilterChanges = Partial<Pick<IncidentQuery, "from" | "to" | "employeeId" | "types" | "status">>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveInt(value: string | undefined): number | null {
  if (value === undefined || !/^\d+$/.test(value)) return null;
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

function parseTypes(value: string | undefined): IncidentType[] {
  const wanted = new Set((value ?? "").split(","));
  return INCIDENT_TYPES.filter((type) => wanted.has(type));
}

function parseStatus(value: string | undefined): IncidentStatus {
  return value !== undefined && Object.hasOwn(STATUS_LABELS, value) ? (value as IncidentStatus) : "all";
}

export function parseIncidentQuery(params: UrlParams): IncidentQuery | null {
  const from = first(params.desde);
  const to = first(params.hasta);
  if (!isIsoDate(from) || !isIsoDate(to)) return null;
  return {
    from,
    to,
    employeeId: positiveInt(first(params.empleado)),
    types: parseTypes(first(params.tipo)),
    status: parseStatus(first(params.estado)),
    page: positiveInt(first(params.pag)) ?? 1,
    rhPage: positiveInt(first(params.pag_rh)) ?? 1,
  };
}

export function incidentQueryString(query: IncidentQuery): string {
  const params = new URLSearchParams({ desde: query.from, hasta: query.to });
  if (query.employeeId !== null) params.set("empleado", String(query.employeeId));
  if (query.types.length > 0) params.set("tipo", query.types.join(","));
  if (query.status !== "all") params.set("estado", query.status);
  if (query.page > 1) params.set("pag", String(query.page));
  if (query.rhPage > 1) params.set("pag_rh", String(query.rhPage));
  return params.toString().replaceAll("%2C", ",");
}

export function withFilters(query: IncidentQuery, changes: FilterChanges): IncidentQuery {
  return { ...query, ...changes, page: 1, rhPage: 1 };
}

export function toApiParams(
  query: IncidentQuery,
  page: number,
  limit: number = PAGE_SIZE,
): IncidentApiParams {
  return {
    from: query.from,
    to: query.to,
    ...(query.employeeId !== null && { employee_id: query.employeeId }),
    ...(query.types.length > 0 && { type: query.types }),
    status: query.status,
    page,
    limit,
  };
}
