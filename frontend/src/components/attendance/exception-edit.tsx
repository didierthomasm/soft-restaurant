"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useDeleteException, useUpdateException } from "@/lib/api/attendance";
import type { ExceptionRef, ExceptionUpdate, RhType } from "@/lib/api/types";
import { formatDate } from "@/lib/dates";
import { ABSENCE_RH_TYPES, EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

type Props = { exception: ExceptionRef; onDone: () => void };

function bodyFrom(form: FormData, isAbsence: boolean): ExceptionUpdate {
  return {
    date_from: String(form.get("date_from")),
    date_to: String(form.get("date_to")),
    comment: String(form.get("comment") ?? "").trim(),
    ...(isAbsence && { rh_type: String(form.get("rh_type")) as RhType }),
  };
}

export function ExceptionEdit({ exception, onDone }: Props) {
  const update = useUpdateException();
  const remove = useDeleteException();
  const isAbsence = exception.kind === "WORK_TO_ABSENCE";

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = bodyFrom(new FormData(event.currentTarget), isAbsence);
    update.mutate(
      { id: exception.id, body },
      {
        onSuccess: () => {
          toast.success("Excepción actualizada");
          onDone();
        },
      },
    );
  }

  function onDelete() {
    remove.mutate(exception.id, {
      onSuccess: () => {
        toast.success("Excepción eliminada");
        onDone();
      },
    });
  }

  return (
    <section className="space-y-3">
      <h3 className="font-medium">Excepción · {EXCEPTION_KIND_LABELS[exception.kind]}</h3>
      {exception.date_from !== exception.date_to && (
        <p className="text-sm text-muted-foreground">
          Aplica del {formatDate(exception.date_from)} al {formatDate(exception.date_to)}; los
          cambios afectan todo el rango.
        </p>
      )}
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="exception_edit_from">Desde</Label>
            <Input id="exception_edit_from" name="date_from" type="date" defaultValue={exception.date_from} required />
          </div>
          <div className="space-y-1">
            <Label htmlFor="exception_edit_to">Hasta</Label>
            <Input id="exception_edit_to" name="date_to" type="date" defaultValue={exception.date_to} required />
          </div>
        </div>
        {isAbsence && (
          <div className="space-y-1">
            <Label htmlFor="exception_edit_rh_type">Tipo en RH</Label>
            <NativeSelect
              id="exception_edit_rh_type"
              name="rh_type"
              defaultValue={exception.rh_type ?? ABSENCE_RH_TYPES[0]}
            >
              {ABSENCE_RH_TYPES.map((option) => (
                <option key={option} value={option}>
                  {RH_LABELS[option]}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
        <div className="space-y-1">
          <Label htmlFor="exception_edit_comment">Comentario</Label>
          <Input id="exception_edit_comment" name="comment" maxLength={500} defaultValue={exception.comment} />
        </div>
        <FormError error={update.error} />
        <Button type="submit" disabled={update.isPending}>
          Guardar cambios
        </Button>
      </form>
      <FormError error={remove.error} />
      <ConfirmDeleteButton label="Eliminar excepción" pending={remove.isPending} onConfirm={onDelete} />
    </section>
  );
}
