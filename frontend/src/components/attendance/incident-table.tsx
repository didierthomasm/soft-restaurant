"use client";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentAction } from "@/lib/labels";

type Props = {
  days: DayOut[];
  byId: Map<number, EmployeeRef>;
  onSelect: (day: DayOut) => void;
};

export function IncidentTable({ days, byId, onSelect }: Props) {
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

function IncidentRow({ day, byId, onSelect }: { day: DayOut } & Omit<Props, "days">) {
  const action = incidentAction(day);
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
