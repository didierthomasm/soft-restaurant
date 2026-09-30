"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRestSwap } from "@/lib/api/attendance";
import type { DayOut } from "@/lib/api/types";

type Props = { employeeId: number; day: DayOut; onDone: () => void };

/**
 * Decision #4: the incident goes on the day not worked; another rest day becomes a
 * workday. From an absence we ask for the worked day; from a check-in on a rest day we
 * ask for the day that becomes rest.
 */
export function RestSwapForm({ employeeId, day, onDone }: Props) {
  const mutation = useRestSwap();
  const fromAbsence = day.outcome === "ABSENT";
  const askedLabel = fromAbsence ? "Día de descanso que trabajará" : "Día que descansó a cambio";

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const other = String(new FormData(event.currentTarget).get("other_day"));
    mutation.mutate(
      {
        employee_id: employeeId,
        absent_day: fromAbsence ? day.day : other,
        worked_day: fromAbsence ? other : day.day,
        comment: "Cambio de descanso",
      },
      {
        onSuccess: () => {
          toast.success("Cambio de descanso registrado");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Cambio de descanso</h3>
      <div className="space-y-1">
        <Label htmlFor="other_day">{askedLabel}</Label>
        <Input id="other_day" name="other_day" type="date" required />
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" variant="outline" disabled={mutation.isPending}>
        Registrar cambio
      </Button>
    </form>
  );
}
