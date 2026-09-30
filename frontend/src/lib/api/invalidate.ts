"use client";

import { type QueryKey, useQueryClient } from "@tanstack/react-query";

export function useInvalidate(...keys: QueryKey[]): () => Promise<void> {
  const client = useQueryClient();
  return async () => {
    await Promise.all(keys.map((queryKey) => client.invalidateQueries({ queryKey })));
  };
}
