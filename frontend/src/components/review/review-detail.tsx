"use client";

import { toast } from "sonner";

import { RhTable } from "@/components/attendance/rh-table";
import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { useApproveReview } from "@/lib/api/reviews";
import type { ReviewDetailOut } from "@/lib/api/types";
import { formatDateTime } from "@/lib/dates";
import { PRIORITY_LABELS, STATUS_LABELS, canApprove, groupByPriority } from "@/lib/review";

import { FindingCard } from "./finding-card";

type Props = {
  review: ReviewDetailOut;
  weekMonday: string;
  onRegenerate: () => void;
  regenerating: boolean;
};

export function ReviewDetail({ review, weekMonday, onRegenerate, regenerating }: Props) {
  const approve = useApproveReview();
  const groups = groupByPriority(review.findings, review.narrative?.items ?? null);
  const approvedAt = review.approved_at ? ` · aprobado el ${formatDateTime(review.approved_at)}` : "";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {STATUS_LABELS[review.status]} · datos al {formatDateTime(review.as_of)}
          {approvedAt}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onRegenerate} disabled={regenerating}>
            Generar de nuevo
          </Button>
          {canApprove(review.status) && (
            <Button
              disabled={approve.isPending}
              onClick={() => approve.mutate(review.id, { onSuccess: () => toast.success("Borrador aprobado") })}
            >
              Aprobar
            </Button>
          )}
        </div>
      </div>
      <FormError error={approve.error} />
      {review.stale && (
        <div role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          Los datos cambiaron desde este borrador. Genera uno nuevo para verlos.
        </div>
      )}
      {review.narrative ? (
        <p className="whitespace-pre-line">{review.narrative.summary}</p>
      ) : (
        <div role="status" className="rounded-lg border p-3 text-sm">
          El agente no pudo redactar este borrador{review.error ? `: ${review.error}` : "."} Los
          hallazgos y la lista para RH están completos.
        </div>
      )}
      {review.findings.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin hallazgos esta semana.</p>
      ) : (
        groups.map((group) => {
          const label = group.priority ? `Prioridad ${PRIORITY_LABELS[group.priority].toLowerCase()}` : "Hallazgos";
          return (
            <section key={group.priority ?? "all"} aria-label={label} className="space-y-2">
              <h3 className="font-medium">{label}</h3>
              <ul className="space-y-2">
                {group.entries.map(({ finding, item }) => (
                  <FindingCard key={finding.id} finding={finding} item={item} weekMonday={weekMonday} />
                ))}
              </ul>
            </section>
          );
        })
      )}
      <section className="space-y-2">
        <h3 className="font-medium">Lista para RH</h3>
        <RhTable rows={review.rh_rows} />
      </section>
    </div>
  );
}
