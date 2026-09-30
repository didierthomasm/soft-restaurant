"use client";

import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useCalendar } from "@/lib/api/attendance";
import { addDays, formatDate, isoWeekNumber, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { Legend } from "./legend";
import { WarningsList } from "./warnings-list";
import { type DaySelection, WeekGrid } from "./week-grid";

export function WeekView({ requestedStart }: { requestedStart: string | null }) {
  const buildQuery = useCallback((today: string) => `desde=${weekStart(today)}`, []);
  useEnsurePeriod(requestedStart, buildQuery);
  if (requestedStart === null) return <Loading />;
  return <Week from={weekStart(requestedStart)} />;
}

function Week({ from }: { from: string }) {
  const to = addDays(from, 6);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`Semana ${isoWeekNumber(from)} · ${formatDate(from)} – ${formatDate(to)}`}
          previousHref={`/semana?desde=${addDays(from, -7)}`}
          nextHref={`/semana?desde=${addDays(from, 7)}`}
        />
        <ExportButton from={from} to={to} group="week" />
      </div>
      {calendar.isPending && <Loading />}
      {calendar.isError && <QueryError error={calendar.error} onRetry={() => calendar.refetch()} />}
      {calendar.data && (
        <>
          <WarningsList warnings={calendar.data.warnings} />
          <WeekGrid
            calendar={calendar.data}
            onSelect={(day, employee) => setSelection({ day, employee })}
          />
          <Legend />
        </>
      )}
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
