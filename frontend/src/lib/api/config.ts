"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";

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
