import Link from "next/link";

import { cn } from "@/lib/utils";

type Props = { view: "semana" | "mes"; weekHref: string; monthHref: string };

export function ViewSwitch({ view, weekHref, monthHref }: Props) {
  const options = [
    { key: "semana", label: "Semana", href: weekHref },
    { key: "mes", label: "Mes", href: monthHref },
  ] as const;
  return (
    <nav aria-label="Vista del calendario" className="inline-flex rounded-md border p-0.5">
      {options.map((option) => (
        <Link
          key={option.key}
          href={option.href}
          aria-current={view === option.key ? "page" : undefined}
          className={cn(
            "rounded px-3 py-1 text-sm",
            view === option.key ? "bg-muted font-medium" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </Link>
      ))}
    </nav>
  );
}
