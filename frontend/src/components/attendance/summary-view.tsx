"use client";

import { useCallback } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useSummary } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import { summaryHref } from "@/lib/calendar";
import { addDays, formatMonth, monthRange } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { SummaryTable } from "./summary-table";

export function SummaryView({ month }: { month: string | null }) {
  const buildQuery = useCallback((today: string) => `mes=${today.slice(0, 7)}`, []);
  useEnsurePeriod(month, buildQuery);
  if (month === null) return <Loading />;
  return <Summary month={month} />;
}

function Summary({ month }: { month: string }) {
  const { from, to } = monthRange(`${month}-01`);
  const summary = useSummary(from, to, "month");
  const employees = useEmployees();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Resumen del mes</h1>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={formatMonth(month)}
          previousHref={summaryHref(addDays(from, -1).slice(0, 7))}
          nextHref={summaryHref(addDays(to, 1).slice(0, 7))}
        />
        <ExportButton from={from} to={to} group="month" />
      </div>
      {summary.isPending && <Loading />}
      {summary.isError && <QueryError error={summary.error} onRetry={() => summary.refetch()} />}
      {summary.data && <SummaryTable summaries={summary.data} names={names} />}
    </div>
  );
}
