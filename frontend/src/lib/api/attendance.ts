"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";
import { useInvalidate } from "./invalidate";
import type { ExceptionCreate, Grouping, JustificationCreate, RestSwapCreate } from "./types";

export const attendanceKeys = {
  all: ["attendance"] as const,
  calendar: (from: string, to: string) => ["attendance", "calendar", from, to] as const,
  incidents: (from: string, to: string) => ["attendance", "incidents", from, to] as const,
  summary: (from: string, to: string, group: string) =>
    ["attendance", "summary", from, to, group] as const,
};

export function useCalendar(from: string, to: string) {
  return useQuery({
    queryKey: attendanceKeys.calendar(from, to),
    queryFn: () => unwrap(api.GET("/attendance/calendar", { params: { query: { from, to } } })),
  });
}

export function useIncidents(from: string, to: string) {
  return useQuery({
    queryKey: attendanceKeys.incidents(from, to),
    queryFn: () => unwrap(api.GET("/attendance/incidents", { params: { query: { from, to } } })),
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
