"use client";

import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useCalendar } from "@/lib/api/attendance";
import { type DayFocus, monthHref, weekHref } from "@/lib/calendar";
import { addDays, formatDate, isoWeekNumber, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { Legend } from "./legend";
import { ViewSwitch } from "./view-switch";
import { WarningsList } from "./warnings-list";
import { type DaySelection, findDaySelection, WeekGrid } from "./week-grid";

export function WeekView({
  requestedStart,
  focus = null,
}: {
  requestedStart: string | null;
  focus?: DayFocus | null;
}) {
  const buildQuery = useCallback((today: string) => `vista=semana&desde=${weekStart(today)}`, []);
  useEnsurePeriod(requestedStart, buildQuery);
  if (requestedStart === null) return <Loading />;
  return <Week from={weekStart(requestedStart)} focus={focus} />;
}

function Week({ from, focus }: { from: string; focus: DayFocus | null }) {
  const to = addDays(from, 6);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const [focusDismissed, setFocusDismissed] = useState(false);
  const focused =
    !focusDismissed && focus && calendar.data
      ? findDaySelection(calendar.data, focus.employeeId, focus.day)
      : null;
  function close() {
    setSelection(null);
    setFocusDismissed(true);
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <ViewSwitch view="semana" weekHref={weekHref(from)} monthHref={monthHref(from.slice(0, 7))} />
          <PeriodNav
            label={`Semana ${isoWeekNumber(from)} · ${formatDate(from)} – ${formatDate(to)}`}
            previousHref={weekHref(addDays(from, -7))}
            nextHref={weekHref(addDays(from, 7))}
          />
        </div>
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
      <DayPanel selection={selection ?? focused} onClose={close} />
    </div>
  );
}
