"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { ExceptionEdit } from "@/components/attendance/exception-edit";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateException, useDeleteException } from "@/lib/api/attendance";
import { useEmployees, useExceptions } from "@/lib/api/config";
import type { ExceptionOut } from "@/lib/api/types";
import { addDays, formatDate, todayIso } from "@/lib/dates";
import { EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

const PAST_DAYS = 45;
const FUTURE_DAYS = 365;

export function ExceptionsTab() {
  const [today] = useState(todayIso);
  const from = addDays(today, -PAST_DAYS);
  const to = addDays(today, FUTURE_DAYS);
  const exceptions = useExceptions(from, to);
  const employees = useEmployees();
  const remove = useDeleteException();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));

  return (
    <div className="space-y-6">
      <ClosureForm />
      <p className="text-sm text-muted-foreground">
        Excepciones del {formatDate(from)} al {formatDate(to)}. Las de un empleado se agregan
        desde el Calendario (clic en el día).
      </p>
      <FormError error={remove.error} />
      {exceptions.isPending && <Loading />}
      {exceptions.isError && <QueryError error={exceptions.error} onRetry={() => exceptions.refetch()} />}
      {exceptions.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead>Empleado</TableHead>
              <TableHead>Fechas</TableHead>
              <TableHead>Tipo en RH</TableHead>
              <TableHead>Comentario</TableHead>
              <TableHead>
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {exceptions.data.map((exception) => (
              <TableRow key={exception.id}>
                <TableCell>{EXCEPTION_KIND_LABELS[exception.kind]}</TableCell>
                <TableCell>
                  {exception.employee_id === null ? "Todos" : names.get(exception.employee_id)}
                </TableCell>
                <TableCell>
                  {formatDate(exception.date_from)}
                  {exception.date_to !== exception.date_from && ` – ${formatDate(exception.date_to)}`}
                </TableCell>
                <TableCell>{exception.rh_type ? RH_LABELS[exception.rh_type] : ""}</TableCell>
                <TableCell>{exception.comment}</TableCell>
                <TableCell className="space-x-2 text-right">
                  <EditExceptionDialog
                    exception={exception}
                    owner={exception.employee_id === null ? "Todos" : (names.get(exception.employee_id) ?? "")}
                  />
                  <ConfirmDeleteButton
                    label={`Eliminar ${EXCEPTION_KIND_LABELS[exception.kind]} del ${formatDate(exception.date_from)}`}
                    pending={remove.isPending}
                    onConfirm={() =>
                      remove.mutate(exception.id, { onSuccess: () => toast.success("Excepción eliminada") })
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

/** Spec §6: store closures (Ley Seca, 24–25 Dec, storms) apply to everyone. */
function ClosureForm() {
  const create = useCreateException();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const dateFrom = String(form.get("closure_from"));
    create.mutate(
      {
        kind: "STORE_CLOSED",
        employee_id: null,
        date_from: dateFrom,
        date_to: String(form.get("closure_to") || dateFrom),
        rh_type: null,
        comment: String(form.get("closure_comment") ?? "").trim(),
      },
      { onSuccess: () => toast.success("Cierre registrado") },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4 sm:grid-cols-3">
      <h3 className="font-medium sm:col-span-3">Cerrar el local (aplica a todos)</h3>
      <div className="space-y-1">
        <Label htmlFor="closure_from">Desde</Label>
        <Input id="closure_from" name="closure_from" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="closure_to">Hasta (opcional)</Label>
        <Input id="closure_to" name="closure_to" type="date" />
      </div>
      <div className="space-y-1">
        <Label htmlFor="closure_comment">Motivo</Label>
        <Input id="closure_comment" name="closure_comment" placeholder="Ley Seca, Navidad…" maxLength={500} />
      </div>
      <div className="space-y-2 sm:col-span-3">
        <FormError error={create.error} />
        <Button type="submit" disabled={create.isPending}>
          Registrar cierre
        </Button>
      </div>
    </form>
  );
}

function EditExceptionDialog({ exception, owner }: { exception: ExceptionOut; owner: string }) {
  const [open, setOpen] = useState(false);
  const kind = EXCEPTION_KIND_LABELS[exception.kind];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" aria-label={`Editar ${kind} del ${formatDate(exception.date_from)}`}>
          Editar
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar excepción</DialogTitle>
          <DialogDescription>{owner}</DialogDescription>
        </DialogHeader>
        <ExceptionEdit exception={exception} onDone={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
