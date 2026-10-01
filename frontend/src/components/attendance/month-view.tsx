"use client";

import { useCallback } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useSummary } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import { addDays, monthRange } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { SummaryTable } from "./summary-table";

const MONTHS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export function MonthView({ month }: { month: string | null }) {
  const buildQuery = useCallback((today: string) => `mes=${today.slice(0, 7)}`, []);
  useEnsurePeriod(month, buildQuery);
  if (month === null) return <Loading />;
  return <Month month={month} />;
}

function Month({ month }: { month: string }) {
  const { from, to } = monthRange(`${month}-01`);
  const summary = useSummary(from, to, "month");
  const employees = useEmployees();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));
  const [year, monthNumber] = month.split("-").map(Number);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`${MONTHS[monthNumber - 1]} ${year}`}
          previousHref={`/mes?mes=${addDays(from, -1).slice(0, 7)}`}
          nextHref={`/mes?mes=${addDays(to, 1).slice(0, 7)}`}
        />
        <ExportButton from={from} to={to} group="month" />
      </div>
      {summary.isPending && <Loading />}
      {summary.isError && <QueryError error={summary.error} onRetry={() => summary.refetch()} />}
      {summary.data && <SummaryTable summaries={summary.data} names={names} />}
    </div>
  );
}
