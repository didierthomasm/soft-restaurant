import { Button } from "@/components/ui/button";
import type { PageMeta } from "@/lib/api/client";
import { pageWindow } from "@/lib/pages";

type Props = { meta: PageMeta; label: string; onPage: (page: number) => void };

export function Pagination({ meta, label, onPage }: Props) {
  const { first, last, lastPage, beyond } = pageWindow(meta);
  if (meta.page === 1 && lastPage === 1) return null;
  const summary = beyond ? "Sin resultados en esta página" : `${first}–${last} de ${meta.total}`;
  return (
    <nav aria-label={label} className="flex items-center justify-end gap-2 text-sm">
      <span className="text-muted-foreground">{summary}</span>
      <Button
        size="sm"
        variant="outline"
        disabled={meta.page <= 1}
        onClick={() => onPage(beyond ? lastPage : meta.page - 1)}
      >
        ← Anterior
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={meta.page >= lastPage}
        onClick={() => onPage(meta.page + 1)}
      >
        Siguiente →
      </Button>
    </nav>
  );
}
