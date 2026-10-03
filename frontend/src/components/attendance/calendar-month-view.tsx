"use client";

import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useCalendar } from "@/lib/api/attendance";
import { monthHref, weekHref } from "@/lib/calendar";
import { addDays, formatMonth, monthRange, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { Legend } from "./legend";
import { MonthGrid } from "./month-grid";
import { ViewSwitch } from "./view-switch";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

export function CalendarMonthView({ month }: { month: string | null }) {
  const buildQuery = useCallback((today: string) => `vista=mes&mes=${today.slice(0, 7)}`, []);
  useEnsurePeriod(month, buildQuery);
  if (month === null) return <Loading />;
  return <Month month={month} />;
}

function Month({ month }: { month: string }) {
  const { from, to } = monthRange(`${month}-01`);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <ViewSwitch view="mes" weekHref={weekHref(weekStart(from))} monthHref={monthHref(month)} />
          <PeriodNav
            label={formatMonth(month)}
            previousHref={monthHref(addDays(from, -1).slice(0, 7))}
            nextHref={monthHref(addDays(to, 1).slice(0, 7))}
          />
        </div>
        <ExportButton from={from} to={to} group="month" />
      </div>
      {calendar.isPending && <Loading />}
      {calendar.isError && <QueryError error={calendar.error} onRetry={() => calendar.refetch()} />}
      {calendar.data && (
        <>
          <WarningsList warnings={calendar.data.warnings} />
          <MonthGrid
            calendar={calendar.data}
            onSelect={(day, employee) => setSelection({ day, employee })}
          />
          <Legend short />
        </>
      )}
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
