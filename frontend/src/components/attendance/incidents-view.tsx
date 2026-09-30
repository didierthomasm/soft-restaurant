"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useIncidents } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { addDays, formatDay, formatTime, weekStart } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentFor } from "@/lib/labels";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { RhTable } from "./rh-table";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

type Props = { from: string | null; to: string | null };

export function IncidentsView({ from, to }: Props) {
  const buildQuery = useCallback((today: string) => {
    const start = weekStart(today);
    return `desde=${start}&hasta=${addDays(start, 6)}`;
  }, []);
  useEnsurePeriod(from && to ? from : null, buildQuery);
  if (!from || !to) return <Loading />;
  return <Incidents from={from} to={to} />;
}

function RangeForm({ from, to }: { from: string; to: string }) {
  const router = useRouter();
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    router.push(`/incidencias?desde=${form.get("desde")}&hasta=${form.get("hasta")}`);
  }
  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
      <div className="space-y-1">
        <Label htmlFor="desde">Desde</Label>
        <Input id="desde" name="desde" type="date" defaultValue={from} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="hasta">Hasta</Label>
        <Input id="hasta" name="hasta" type="date" defaultValue={to} required />
      </div>
      <Button type="submit" variant="outline">
        Ver
      </Button>
    </form>
  );
}

function Incidents({ from, to }: { from: string; to: string }) {
  const incidents = useIncidents(from, to);
  const employees = useEmployees();
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const byId = new Map<number, EmployeeRef>((employees.data ?? []).map((e) => [e.id, e]));
  const select = (day: DayOut) => {
    const employee = byId.get(day.employee_id);
    if (employee) setSelection({ day, employee });
  };
  const unresolved = incidents.data?.incidents.filter((d) => d.outcome === "UNREGISTERED_CHANGE") ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <RangeForm from={from} to={to} />
        <ExportButton from={from} to={to} group="week" />
      </div>
      {incidents.isPending && <Loading />}
      {incidents.isError && <QueryError error={incidents.error} onRetry={() => incidents.refetch()} />}
      {incidents.data && (
        <>
          <WarningsList warnings={incidents.data.warnings} />
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Para capturar en RH</h2>
            <RhTable rows={incidents.data.rh_rows} />
          </section>
          {unresolved.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-lg font-semibold">Pendientes de resolver</h2>
              <IncidentTable days={unresolved} byId={byId} onSelect={select} />
            </section>
          )}
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Todas las incidencias</h2>
            <IncidentTable days={incidents.data.incidents} byId={byId} onSelect={select} />
          </section>
        </>
      )}
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}

type TableProps = {
  days: DayOut[];
  byId: Map<number, EmployeeRef>;
  onSelect: (day: DayOut) => void;
};

function IncidentTable({ days, byId, onSelect }: TableProps) {
  if (days.length === 0) return <p className="text-sm text-muted-foreground">Sin incidencias.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empleado</TableHead>
          <TableHead>Día</TableHead>
          <TableHead>Resultado</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>
            <span className="sr-only">Acciones</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {days.map((day) => (
          <IncidentRow key={`${day.employee_id}-${day.day}`} day={day} byId={byId} onSelect={onSelect} />
        ))}
      </TableBody>
    </Table>
  );
}

function IncidentRow({ day, byId, onSelect }: { day: DayOut } & Omit<TableProps, "days">) {
  const justifiable = incidentFor(day.outcome) !== null && day.justification_id === null;
  const justified = incidentFor(day.outcome) !== null && day.justification_id !== null;
  const action = justifiable
    ? "Justificar"
    : justified
      ? "Editar"
      : day.outcome === "UNREGISTERED_CHANGE"
        ? "Resolver"
        : null;
  const status =
    day.justification_id !== null || day.outcome === "JUSTIFIED"
      ? `Justificada${day.rh_type ? ` · ${RH_LABELS[day.rh_type]}` : ""}`
      : "Sin justificar";
  return (
    <TableRow>
      <TableCell>{byId.get(day.employee_id)?.short_name ?? day.employee_id}</TableCell>
      <TableCell>{formatDay(day.day)}</TableCell>
      <TableCell>
        {OUTCOME_LABELS[day.outcome]} {formatTime(day.checkin)}
      </TableCell>
      <TableCell>{status}</TableCell>
      <TableCell className="text-right">
        {action && (
          <Button size="sm" variant="outline" onClick={() => onSelect(day)}>
            {action}
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
