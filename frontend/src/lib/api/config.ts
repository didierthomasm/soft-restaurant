"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";
import { useInvalidate } from "./invalidate";
import type { EmployeeUpdate, RestRuleCreate, SettingsBody } from "./types";

export const configKeys = {
  employees: ["employees"] as const,
  srPreview: ["employees", "sr-preview"] as const,
  restRules: ["rest-rules"] as const,
  exceptions: (from: string, to: string) => ["exceptions", from, to] as const,
  settings: ["settings"] as const,
};

export function useEmployees() {
  return useQuery({
    queryKey: configKeys.employees,
    queryFn: () => unwrap(api.GET("/employees")),
  });
}

const ATTENDANCE = ["attendance"] as const;

export function useUpdateEmployee() {
  const invalidate = useInvalidate(configKeys.employees, ATTENDANCE);
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: EmployeeUpdate }) =>
      unwrap(
        api.PATCH("/employees/{employee_id}", {
          params: { path: { employee_id: id } },
          body: changes,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useSrPreview(enabled: boolean) {
  return useQuery({
    queryKey: configKeys.srPreview,
    queryFn: () => unwrap(api.GET("/employees/sr-preview")),
    enabled,
  });
}

export function useImportEmployees() {
  const invalidate = useInvalidate(configKeys.employees, ATTENDANCE);
  return useMutation({
    mutationFn: (srIds: number[]) =>
      unwrap(api.POST("/employees/import-from-sr", { body: { sr_ids: srIds } })),
    onSuccess: invalidate,
  });
}

export function useRestRules() {
  return useQuery({
    queryKey: configKeys.restRules,
    queryFn: () => unwrap(api.GET("/rest-rules")),
  });
}

export function useCreateRestRule() {
  const invalidate = useInvalidate(configKeys.restRules, ATTENDANCE);
  return useMutation({
    mutationFn: (body: RestRuleCreate) => unwrap(api.POST("/rest-rules", { body })),
    onSuccess: invalidate,
  });
}

export function useDeleteRestRule() {
  const invalidate = useInvalidate(configKeys.restRules, ATTENDANCE);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/rest-rules/{rule_id}", { params: { path: { rule_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useExceptions(from: string, to: string) {
  return useQuery({
    queryKey: configKeys.exceptions(from, to),
    queryFn: () => unwrap(api.GET("/exceptions", { params: { query: { from, to } } })),
  });
}

export function useDeleteException() {
  const invalidate = useInvalidate(["exceptions"], ATTENDANCE);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/exceptions/{exception_id}", { params: { path: { exception_id: id } } }),
      ),
    onSuccess: invalidate,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: configKeys.settings,
    queryFn: () => unwrap(api.GET("/settings")),
  });
}

export function useSaveSettings() {
  const invalidate = useInvalidate(configKeys.settings, ATTENDANCE);
  return useMutation({
    mutationFn: (body: SettingsBody) => unwrap(api.PUT("/settings", { body })),
    onSuccess: invalidate,
  });
}
