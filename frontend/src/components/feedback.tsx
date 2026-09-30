import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

export function Loading() {
  return <p className="text-sm text-muted-foreground">Cargando…</p>;
}

export function QueryError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm"
    >
      <span>{message}</span>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  );
}

export function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "No se pudo guardar";
  return (
    <p role="alert" className="text-sm text-destructive">
      {message}
    </p>
  );
}
