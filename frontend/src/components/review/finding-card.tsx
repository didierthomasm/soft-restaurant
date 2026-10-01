import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { FindingOut, NarrativeItemOut } from "@/lib/api/types";
import { FINDING_LABELS, actionHref, actionLabel, describeFacts, formatDays } from "@/lib/review";

type Props = { finding: FindingOut; item: NarrativeItemOut | null; weekMonday: string };

export function FindingCard({ finding, item, weekMonday }: Props) {
  const title = `${FINDING_LABELS[finding.kind]}${finding.employee_name ? ` · ${finding.employee_name}` : ""}`;
  const facts = describeFacts(finding);
  const href = actionHref(finding, weekMonday);
  return (
    <li className="space-y-1 rounded-lg border p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium">{title}</p>
        {finding.days.length > 0 && (
          <p className="text-xs text-muted-foreground">{formatDays(finding.days)}</p>
        )}
      </div>
      {facts && <p className="text-sm text-muted-foreground">{facts}</p>}
      {item && <p className="text-sm">{item.explanation}</p>}
      {href && (
        <Button asChild variant="outline" size="sm">
          <Link href={href}>{actionLabel(finding, item)}</Link>
        </Button>
      )}
    </li>
  );
}
