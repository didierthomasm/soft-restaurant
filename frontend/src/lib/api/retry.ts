import { ApiError, isSrUnavailable } from "./client";

const MAX_RETRIES = 2;

/** Retry policy for queries: never hammer a down POS, never retry client errors. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (isSrUnavailable(error)) return false;
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < MAX_RETRIES;
}
