"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useCreateJustification } from "@/lib/api/attendance";
import type { Incident, RhType } from "@/lib/api/types";
import { JUSTIFICATION_RH_TYPES, RH_LABELS } from "@/lib/labels";

type Props = { employeeId: number; day: string; incident: Incident; onDone: () => void };

export function JustifyForm({ employeeId, day, incident, onDone }: Props) {
  const mutation = useCreateJustification();
  const options = JUSTIFICATION_RH_TYPES[incident];

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate(
      {
        employee_id: employeeId,
        day,
        incident,
        reason: String(form.get("reason") ?? "").trim(),
        rh_type: String(form.get("rh_type")) as RhType,
      },
      {
        onSuccess: () => {
          toast.success("Justificación guardada");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Justificar {incident === "LATE" ? "retardo" : "falta"}</h3>
      <div className="space-y-1">
        <Label htmlFor="reason">Motivo</Label>
        <Input id="reason" name="reason" required maxLength={500} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="rh_type">Tipo en RH</Label>
        <NativeSelect id="rh_type" name="rh_type" defaultValue={options[0]}>
          {options.map((option) => (
            <option key={option} value={option}>
              {RH_LABELS[option]}
            </option>
          ))}
        </NativeSelect>
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" disabled={mutation.isPending}>
        Guardar justificación
      </Button>
    </form>
  );
}
