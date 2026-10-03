import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "./client";
import { useInvalidate } from "./invalidate";
import type {
  ExceptionCreate,
  ExceptionUpdate,
  Grouping,
  IncidentStatus,
  IncidentType,
  JustificationCreate,
  JustificationUpdate,
  RestSwapCreate,
} from "./types";

export type IncidentApiParams = {
  from: string;
  to: string;
  employee_id?: number;
  type?: IncidentType[];
  status: IncidentStatus;
  page: number;
  limit: number;
};

export const attendanceKeys = {
  all: ["attendance"] as const,
  calendar: (from: string, to: string) => ["attendance", "calendar", from, to] as const,
  incidents: (params: IncidentApiParams) => ["attendance", "incidents", params] as const,
  rhRows: (params: IncidentApiParams) => ["attendance", "rh-rows", params] as const,
  summary: (from: string, to: string, group: string) =>
    ["attendance", "summary", from, to, group] as const,
};

export function useCalendar(from: string, to: string) {
  return useQuery({
    queryKey: attendanceKeys.calendar(from, to),
    queryFn: () => unwrap(api.GET("/attendance/calendar", { params: { query: { from, to } } })),
  });
}

export function useIncidents(params: IncidentApiParams) {
  return useQuery({
    queryKey: attendanceKeys.incidents(params),
    queryFn: () => unwrapPage(api.GET("/attendance/incidents", { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}

export function useRhRows(params: IncidentApiParams) {
  return useQuery({
    queryKey: attendanceKeys.rhRows(params),
    queryFn: () => unwrapPage(api.GET("/attendance/rh-rows", { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}

export function useSummary(from: string, to: string, group: Grouping) {
  return useQuery({
    queryKey: attendanceKeys.summary(from, to, group),
    queryFn: () =>
      unwrap(api.GET("/attendance/summary", { params: { query: { from, to, group } } })),
  });
}

export function useCreateJustification() {
  const invalidate = useInvalidate(attendanceKeys.all);
  return useMutation({
    mutationFn: (body: JustificationCreate) => unwrap(api.POST("/justifications", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateJustification() {
  const invalidate = useInvalidate(attendanceKeys.all);
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: JustificationUpdate }) =>
      unwrap(
        api.PATCH("/justifications/{justification_id}", {
          params: { path: { justification_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteJustification() {
  const invalidate = useInvalidate(attendanceKeys.all);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/justifications/{justification_id}", {
          params: { path: { justification_id: id } },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useRestSwap() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (body: RestSwapCreate) => unwrap(api.POST("/exceptions/rest-swap", { body })),
    onSuccess: invalidate,
  });
}

export function useCreateException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (body: ExceptionCreate) => unwrap(api.POST("/exceptions", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ExceptionUpdate }) =>
      unwrap(
        api.PATCH("/exceptions/{exception_id}", {
          params: { path: { exception_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/exceptions/{exception_id}", { params: { path: { exception_id: id } } }),
      ),
    onSuccess: invalidate,
  });
}
