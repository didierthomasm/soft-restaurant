"use client";

import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import type { EmployeeRef, IncidentStatus, IncidentType } from "@/lib/api/types";
import { type IncidentQuery, withFilters } from "@/lib/incident-query";
import { INCIDENT_TYPES, OUTCOME_LABELS, STATUS_LABELS } from "@/lib/labels";

type Props = {
  query: IncidentQuery;
  employees: EmployeeRef[];
  onApply: (query: IncidentQuery) => void;
};

function readForm(query: IncidentQuery, form: FormData): IncidentQuery {
  const employee = String(form.get("empleado") ?? "");
  const wanted = new Set(form.getAll("tipo").map(String));
  return withFilters(query, {
    from: String(form.get("desde")),
    to: String(form.get("hasta")),
    employeeId: employee === "" ? null : Number(employee),
    types: INCIDENT_TYPES.filter((type: IncidentType) => wanted.has(type)),
    status: String(form.get("estado")) as IncidentStatus,
  });
}

export function IncidentFilters({ query, employees, onApply }: Props) {
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply(readForm(query, new FormData(event.currentTarget)));
  }
  const clear = () => onApply(withFilters(query, { employeeId: null, types: [], status: "all" }));
  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <Label htmlFor="desde">Desde</Label>
        <Input id="desde" name="desde" type="date" defaultValue={query.from} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="hasta">Hasta</Label>
        <Input id="hasta" name="hasta" type="date" defaultValue={query.to} required />
      </div>
      <div className="space-y-1">
        {/* Remount when the options arrive: defaultValue only applies on mount. */}
        <Label htmlFor="empleado">Empleado</Label>
        <NativeSelect
          key={employees.length}
          id="empleado"
          name="empleado"
          defaultValue={query.employeeId ?? ""}
        >
          <option value="">Todos</option>
          {employees.map((employee) => (
            <option key={employee.id} value={employee.id}>
              {employee.short_name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <fieldset className="flex flex-wrap items-center gap-3 pb-2">
        <legend className="sr-only">Tipo</legend>
        {INCIDENT_TYPES.map((type) => (
          <label key={type} className="flex items-center gap-1 text-sm">
            <input
              type="checkbox"
              name="tipo"
              value={type}
              defaultChecked={query.types.includes(type)}
              className="size-4 accent-primary"
            />
            {OUTCOME_LABELS[type]}
          </label>
        ))}
      </fieldset>
      <div className="space-y-1">
        <Label htmlFor="estado">Estado</Label>
        <NativeSelect id="estado" name="estado" defaultValue={query.status}>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </NativeSelect>
      </div>
      <Button type="submit" variant="outline">
        Ver
      </Button>
      <Button type="button" variant="ghost" onClick={clear}>
        Limpiar filtros
      </Button>
    </form>
  );
}
