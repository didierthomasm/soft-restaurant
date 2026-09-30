"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RhRowOut } from "@/lib/api/types";
import { formatDate } from "@/lib/dates";
import { RH_LABELS } from "@/lib/labels";
import { rhRowsToTsv } from "@/lib/tsv";

export function RhTable({ rows }: { rows: RhRowOut[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin incidencias para capturar en RH.</p>;
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(rhRowsToTsv(rows));
      toast.success("Lista copiada");
    } catch {
      toast.error("No se pudo copiar; selecciona la tabla manualmente");
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <Button variant="outline" onClick={copy}>
          Copiar para RH
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre en RH</TableHead>
            <TableHead>Fecha</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Comentario</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={`${row.employee_id}-${row.day}-${row.rh_type}`}>
              <TableCell>{row.name}</TableCell>
              <TableCell>{formatDate(row.day)}</TableCell>
              <TableCell>{RH_LABELS[row.rh_type]}</TableCell>
              <TableCell>{row.comment}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
