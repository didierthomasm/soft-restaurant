"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { todayIso } from "./dates";

/**
 * Pages without a period in the URL get one computed in the browser (local time), never
 * on the server, which runs in UTC and would show the wrong week around midnight.
 */
export function useEnsurePeriod(
  requested: string | null,
  buildQuery: (today: string) => string,
): void {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (requested === null) router.replace(`${pathname}?${buildQuery(todayIso())}`);
  }, [requested, pathname, router, buildQuery]);
}
