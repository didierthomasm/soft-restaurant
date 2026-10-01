"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useCreateException } from "@/lib/api/attendance";
import type { ExceptionKind, RhType } from "@/lib/api/types";
import { ABSENCE_RH_TYPES, EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

const EMPLOYEE_KINDS: ExceptionKind[] = [
  "WORK_TO_ABSENCE",
  "PRESENT_NO_CHECKIN",
  "REST_TO_WORK",
  "MANUAL_ABSENCE",
];

type Props = { employeeId: number; day: string; onDone: () => void };

export function ExceptionForm({ employeeId, day, onDone }: Props) {
  const mutation = useCreateException();
  const [kind, setKind] = useState<ExceptionKind>("WORK_TO_ABSENCE");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate(
      {
        kind,
        employee_id: employeeId,
        date_from: day,
        date_to: String(form.get("date_to") || day),
        rh_type: kind === "WORK_TO_ABSENCE" ? (String(form.get("rh_type")) as RhType) : null,
        comment: String(form.get("comment") ?? "").trim(),
      },
      {
        onSuccess: () => {
          toast.success("Excepción registrada");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Agregar excepción</h3>
      <div className="space-y-1">
        <Label htmlFor="kind">Tipo</Label>
        <NativeSelect id="kind" value={kind} onChange={(e) => setKind(e.target.value as ExceptionKind)}>
          {EMPLOYEE_KINDS.map((option) => (
            <option key={option} value={option}>
              {EXCEPTION_KIND_LABELS[option]}
            </option>
          ))}
        </NativeSelect>
      </div>
      {kind === "WORK_TO_ABSENCE" && (
        <div className="space-y-1">
          <Label htmlFor="exception_rh_type">Tipo en RH</Label>
          <NativeSelect id="exception_rh_type" name="rh_type" defaultValue="VACACIONES">
            {ABSENCE_RH_TYPES.map((option) => (
              <option key={option} value={option}>
                {RH_LABELS[option]}
              </option>
            ))}
          </NativeSelect>
        </div>
      )}
      <div className="space-y-1">
        <Label htmlFor="date_to">Hasta (opcional)</Label>
        <Input id="date_to" name="date_to" type="date" min={day} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="comment">Comentario</Label>
        <Input id="comment" name="comment" maxLength={500} />
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" variant="outline" disabled={mutation.isPending}>
        Guardar excepción
      </Button>
    </form>
  );
}
