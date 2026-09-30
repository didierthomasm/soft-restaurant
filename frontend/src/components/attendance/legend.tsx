import type { Outcome } from "@/lib/api/types";
import { OUTCOME_LABELS, OUTCOME_STYLES } from "@/lib/labels";
import { cn } from "@/lib/utils";

const SHOWN: Outcome[] = ["OK", "LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED", "REST", "CLOSED"];

export function Legend() {
  return (
    <ul aria-label="Leyenda" className="flex flex-wrap gap-2 text-xs">
      {SHOWN.map((outcome) => (
        <li key={outcome} className={cn("rounded px-2 py-1", OUTCOME_STYLES[outcome])}>
          {OUTCOME_LABELS[outcome]}
        </li>
      ))}
    </ul>
  );
}
