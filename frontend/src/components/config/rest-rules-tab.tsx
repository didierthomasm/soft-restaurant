"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateRestRule, useDeleteRestRule, useEmployees, useRestRules } from "@/lib/api/config";
import { formatDate } from "@/lib/dates";
import { WEEKDAY_LABELS } from "@/lib/labels";

export function RestRulesTab() {
  const rules = useRestRules();
  const employees = useEmployees();
  const remove = useDeleteRestRule();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));

  return (
    <div className="space-y-6">
      <RestRuleForm employees={employees.data ?? []} />
      <FormError error={remove.error} />
      {rules.isPending && <Loading />}
      {rules.isError && <QueryError error={rules.error} onRetry={() => rules.refetch()} />}
      {rules.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empleado</TableHead>
              <TableHead>Día fijo</TableHead>
              <TableHead>Día extra (cada 2 semanas)</TableHead>
              <TableHead>Semana doble desde</TableHead>
              <TableHead>Vigencia</TableHead>
              <TableHead>
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.data.map((rule) => (
              <TableRow key={rule.id}>
                <TableCell>{names.get(rule.employee_id) ?? rule.employee_id}</TableCell>
                <TableCell>{WEEKDAY_LABELS[rule.fixed_weekday]}</TableCell>
                <TableCell>{WEEKDAY_LABELS[rule.extra_weekday]}</TableCell>
                <TableCell>{formatDate(rule.double_rest_anchor)}</TableCell>
                <TableCell>
                  {formatDate(rule.valid_from)} – {rule.valid_to ? formatDate(rule.valid_to) : "vigente"}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => remove.mutate(rule.id, { onSuccess: () => toast.success("Regla eliminada") })}
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function WeekdaySelect({ id, name, defaultValue }: { id: string; name: string; defaultValue: number }) {
  return (
    <NativeSelect id={id} name={name} defaultValue={String(defaultValue)}>
      {WEEKDAY_LABELS.map((label, index) => (
        <option key={label} value={index}>
          {label}
        </option>
      ))}
    </NativeSelect>
  );
}

function RestRuleForm({ employees }: { employees: { id: number; short_name: string }[] }) {
  const create = useCreateRestRule();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const validTo = String(form.get("valid_to") ?? "");
    create.mutate(
      {
        employee_id: Number(form.get("employee_id")),
        fixed_weekday: Number(form.get("fixed_weekday")),
        extra_weekday: Number(form.get("extra_weekday")),
        double_rest_anchor: String(form.get("double_rest_anchor")),
        valid_from: String(form.get("valid_from")),
        valid_to: validTo || null,
      },
      { onSuccess: () => toast.success("Regla creada") },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4 sm:grid-cols-3">
      <h3 className="font-medium sm:col-span-3">Nueva regla de descanso</h3>
      <div className="space-y-1">
        <Label htmlFor="rule_employee">Empleado</Label>
        <NativeSelect id="rule_employee" name="employee_id" required>
          {employees.map((e) => (
            <option key={e.id} value={e.id}>
              {e.short_name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="space-y-1">
        <Label htmlFor="fixed_weekday">Día fijo</Label>
        <WeekdaySelect id="fixed_weekday" name="fixed_weekday" defaultValue={1} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="extra_weekday">Día extra</Label>
        <WeekdaySelect id="extra_weekday" name="extra_weekday" defaultValue={0} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="double_rest_anchor">Un lunes con descanso doble</Label>
        <Input id="double_rest_anchor" name="double_rest_anchor" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="valid_from">Vigente desde</Label>
        <Input id="valid_from" name="valid_from" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="valid_to">Hasta (opcional)</Label>
        <Input id="valid_to" name="valid_to" type="date" />
      </div>
      <div className="space-y-2 sm:col-span-3">
        <FormError error={create.error} />
        <Button type="submit" disabled={create.isPending || employees.length === 0}>
          Crear regla
        </Button>
      </div>
    </form>
  );
}
