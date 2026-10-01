"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { Button } from "@/components/ui/button";
import { useCreateReview, useRecentReviews, useReview, useWeekReviews } from "@/lib/api/reviews";
import type { ReviewSummaryOut } from "@/lib/api/types";
import { addDays, formatDate, formatDateTime, isoWeekNumber, isoWeekYear, todayIso, weekStart } from "@/lib/dates";
import { STATUS_LABELS, TRIGGER_LABELS, defaultReviewMonday, isInProgress } from "@/lib/review";

import { ReviewDetail } from "./review-detail";

export function ReviewView({ requestedStart }: { requestedStart: string | null }) {
  if (requestedStart === null) return <RedirectToDefaultWeek />;
  return <WeekReviews monday={weekStart(requestedStart)} />;
}

function RedirectToDefaultWeek() {
  const router = useRouter();
  const recent = useRecentReviews();
  const pending = recent.isPending;
  const latest = recent.data?.[0];
  useEffect(() => {
    if (pending) return;
    router.replace(`/revision?desde=${defaultReviewMonday(latest, todayIso())}`);
  }, [pending, latest, router]);
  return <Loading />;
}

export function WeekReviews({ monday }: { monday: string }) {
  const year = isoWeekYear(monday);
  const week = isoWeekNumber(monday);
  const reviews = useWeekReviews(year, week);
  const create = useCreateReview();
  const latest = reviews.data?.[0] ?? null;
  const generate = () =>
    create.mutate({ year, week }, { onSuccess: () => toast.success("Generando borrador…") });
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`Semana ${week} · ${formatDate(monday)} – ${formatDate(addDays(monday, 6))}`}
          previousHref={`/revision?desde=${addDays(monday, -7)}`}
          nextHref={`/revision?desde=${addDays(monday, 7)}`}
        />
        {reviews.data && !latest && (
          <Button onClick={generate} disabled={create.isPending}>
            Generar borrador
          </Button>
        )}
      </div>
      <FormError error={create.error} />
      {reviews.isPending && <Loading />}
      {reviews.isError && <QueryError error={reviews.error} onRetry={() => reviews.refetch()} />}
      {reviews.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">Todavía no hay borrador para esta semana.</p>
      )}
      {latest && (
        <LatestReview summary={latest} monday={monday} onRegenerate={generate} busy={create.isPending} />
      )}
      {reviews.data && reviews.data.length > 1 && <History reviews={reviews.data.slice(1)} />}
    </div>
  );
}

type LatestProps = {
  summary: ReviewSummaryOut;
  monday: string;
  onRegenerate: () => void;
  busy: boolean;
};

function LatestReview({ summary, monday, onRegenerate, busy }: LatestProps) {
  const detail = useReview(summary.id);
  const status = detail.data?.status ?? summary.status;
  if (isInProgress(status)) {
    return (
      <p role="status" className="text-sm">
        Generando borrador… ({STATUS_LABELS[status].toLowerCase()})
      </p>
    );
  }
  if (status === "FAILED") {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm"
      >
        <span>No se pudo generar el borrador: {detail.data?.error ?? summary.error}</span>
        <Button variant="outline" size="sm" onClick={onRegenerate} disabled={busy}>
          Intentar de nuevo
        </Button>
      </div>
    );
  }
  if (detail.isError) return <QueryError error={detail.error} onRetry={() => detail.refetch()} />;
  if (!detail.data) return <Loading />;
  return <ReviewDetail review={detail.data} weekMonday={monday} onRegenerate={onRegenerate} regenerating={busy} />;
}

function History({ reviews }: { reviews: ReviewSummaryOut[] }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">
        Borradores anteriores de esta semana ({reviews.length})
      </summary>
      <ul className="mt-2 space-y-1">
        {reviews.map((review) => (
          <li key={review.id}>
            {TRIGGER_LABELS[review.trigger]} · {STATUS_LABELS[review.status]}
            {review.as_of && ` · datos al ${formatDateTime(review.as_of)}`}
          </li>
        ))}
      </ul>
    </details>
  );
}
