"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useDeleteJustification, useUpdateJustification } from "@/lib/api/attendance";
import type { Incident, RhType } from "@/lib/api/types";
import { JUSTIFICATION_RH_TYPES, RH_LABELS } from "@/lib/labels";

type Props = {
  justificationId: number;
  incident: Incident;
  rhType: RhType | null;
  reason: string;
  onDone: () => void;
};

export function JustificationEdit({ justificationId, incident, rhType, reason, onDone }: Props) {
  const update = useUpdateJustification();
  const remove = useDeleteJustification();
  const options = JUSTIFICATION_RH_TYPES[incident];
  const current = rhType && options.includes(rhType) ? rhType : options[0];

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selected = String(new FormData(event.currentTarget).get("rh_type")) as RhType;
    update.mutate(
      { id: justificationId, body: { rh_type: selected } },
      {
        onSuccess: () => {
          toast.success("Justificación actualizada");
          onDone();
        },
      },
    );
  }

  function onDelete() {
    remove.mutate(justificationId, {
      onSuccess: () => {
        toast.success("Justificación eliminada");
        onDone();
      },
    });
  }

  return (
    <section className="space-y-3">
      <h3 className="font-medium">Justificación</h3>
      <p className="text-sm">
        {rhType ? RH_LABELS[rhType] : "Sin tipo en RH"}
        {reason && ` · ${reason}`}
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="edit_rh_type">Tipo en RH</Label>
          <NativeSelect id="edit_rh_type" name="rh_type" defaultValue={current}>
            {options.map((option) => (
              <option key={option} value={option}>
                {RH_LABELS[option]}
              </option>
            ))}
          </NativeSelect>
        </div>
        <FormError error={update.error} />
        <Button type="submit" disabled={update.isPending}>
          Cambiar tipo en RH
        </Button>
      </form>
      <FormError error={remove.error} />
      <ConfirmDeleteButton
        label="Eliminar justificación"
        pending={remove.isPending}
        onConfirm={onDelete}
      />
    </section>
  );
}
