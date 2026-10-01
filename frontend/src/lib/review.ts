import type { ReviewStatus } from "@/lib/api/types";

export function isInProgress(status: ReviewStatus): boolean {
  return status === "QUEUED" || status === "RUNNING";
}
