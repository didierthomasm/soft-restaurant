"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentFor } from "@/lib/labels";

import { ExceptionForm } from "./exception-form";
import { JustificationEdit } from "./justification-edit";
import { JustifyForm } from "./justify-form";
import { RestSwapForm } from "./rest-swap-form";
import type { DaySelection } from "./week-grid";

type Props = { selection: DaySelection | null; onClose: () => void };

export function DayPanel({ selection, onClose }: Props) {
  return (
    <Sheet open={selection !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {selection && <DayDetail selection={selection} onDone={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function describe({ day }: DaySelection): string {
  const parts = [OUTCOME_LABELS[day.outcome]];
  if (day.checkin) parts.push(`checó ${formatTime(day.checkin)}`);
  if (day.minutes_late) parts.push(`${day.minutes_late} min tarde`);
  if (day.rh_type) parts.push(RH_LABELS[day.rh_type]);
  return parts.join(" · ");
}

function DayDetail({ selection, onDone }: { selection: DaySelection; onDone: () => void }) {
  const { day, employee } = selection;
  const incident = incidentFor(day.outcome);
  const canSwap = day.outcome === "ABSENT" || day.outcome === "UNREGISTERED_CHANGE";
  return (
    <>
      <SheetHeader>
        <SheetTitle>
          {employee.short_name} · {formatDay(day.day)}
        </SheetTitle>
        <SheetDescription>{describe(selection)}</SheetDescription>
      </SheetHeader>
      <div className="space-y-8 p-4">
        {day.comment && day.justification_id === null && <p className="text-sm">{day.comment}</p>}
        {incident && day.justification_id === null && (
          <JustifyForm employeeId={employee.id} day={day.day} incident={incident} onDone={onDone} />
        )}
        {incident && day.justification_id !== null && (
          <JustificationEdit
            justificationId={day.justification_id}
            incident={incident}
            rhType={day.rh_type}
            reason={day.comment}
            onDone={onDone}
          />
        )}
        {canSwap && <RestSwapForm employeeId={employee.id} day={day} onDone={onDone} />}
        <ExceptionForm employeeId={employee.id} day={day.day} onDone={onDone} />
      </div>
    </>
  );
}
