import type { WarningOut } from "@/lib/api/types";
import { WARNING_LABELS } from "@/lib/labels";

export function WarningsList({ warnings }: { warnings: WarningOut[] }) {
  if (warnings.length === 0) return null;
  return (
    <section aria-label="Avisos" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
      <ul className="space-y-1">
        {warnings.map((warning, index) => (
          <li key={`${warning.code}-${warning.employee_id}-${warning.day}-${index}`}>
            <span className="font-medium">{WARNING_LABELS[warning.code]}:</span> {warning.detail}
          </li>
        ))}
      </ul>
    </section>
  );
}
