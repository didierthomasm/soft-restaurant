"use client";

import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useEmployees, useUpdateEmployee } from "@/lib/api/config";
import type { Area, EmployeeOut, EmployeeUpdate } from "@/lib/api/types";

import { ImportDialog } from "./import-dialog";

const FLAGS = [
  { field: "applies_lateness", label: "Aplica retardos" },
  { field: "tracks_attendance", label: "Checa en SR" },
  { field: "active", label: "Activo" },
] as const;

export function EmployeesTab() {
  const employees = useEmployees();
  const update = useUpdateEmployee();
  const save = (id: number, changes: EmployeeUpdate) =>
    update.mutate({ id, changes }, { onSuccess: () => toast.success("Empleado actualizado") });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <ImportDialog />
      </div>
      <FormError error={update.error} />
      {employees.isPending && <Loading />}
      {employees.isError && <QueryError error={employees.error} onRetry={() => employees.refetch()} />}
      {employees.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Id SR</TableHead>
              <TableHead>Nombre corto</TableHead>
              <TableHead>Nombre en RH</TableHead>
              <TableHead>Área</TableHead>
              {FLAGS.map((flag) => (
                <TableHead key={flag.field}>{flag.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {employees.data.map((employee) => (
              <EmployeeRow key={employee.id} employee={employee} onSave={save} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

type RowProps = { employee: EmployeeOut; onSave: (id: number, changes: EmployeeUpdate) => void };

function EmployeeRow({ employee, onSave }: RowProps) {
  return (
    <TableRow>
      <TableCell>{employee.sr_id ?? "—"}</TableCell>
      <TableCell>{employee.short_name}</TableCell>
      <TableCell>
        <Input
          aria-label={`Nombre en RH de ${employee.short_name}`}
          defaultValue={employee.rh_name ?? ""}
          maxLength={160}
          onBlur={(event) => {
            const value = event.target.value.trim() || null;
            if (value !== employee.rh_name) onSave(employee.id, { rh_name: value });
          }}
        />
      </TableCell>
      <TableCell>
        <NativeSelect
          aria-label={`Área de ${employee.short_name}`}
          value={employee.area}
          onChange={(event) => onSave(employee.id, { area: event.target.value as Area })}
        >
          <option value="OTHER">Barra / servicio</option>
          <option value="KITCHEN">Cocina</option>
        </NativeSelect>
      </TableCell>
      {FLAGS.map((flag) => (
        <TableCell key={flag.field}>
          <Checkbox
            aria-label={`${flag.label}: ${employee.short_name}`}
            checked={employee[flag.field]}
            onCheckedChange={(checked) =>
              onSave(employee.id, { [flag.field]: checked === true } as EmployeeUpdate)
            }
          />
        </TableCell>
      ))}
    </TableRow>
  );
}
