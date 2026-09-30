import Link from "next/link";

import { Button } from "@/components/ui/button";

type Props = { label: string; previousHref: string; nextHref: string };

export function PeriodNav({ label, previousHref, nextHref }: Props) {
  return (
    <div className="flex items-center gap-2">
      <Button asChild variant="outline" size="sm">
        <Link href={previousHref}>← Anterior</Link>
      </Button>
      <span className="text-sm font-medium">{label}</span>
      <Button asChild variant="outline" size="sm">
        <Link href={nextHref}>Siguiente →</Link>
      </Button>
    </div>
  );
}
