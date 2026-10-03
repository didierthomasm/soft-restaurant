"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RhRowOut } from "@/lib/api/types";
import { formatDate } from "@/lib/dates";
import { RH_LABELS } from "@/lib/labels";
import { copyText } from "@/lib/clipboard";
import { rhRowsToTsv } from "@/lib/tsv";

type Props = { rows: RhRowOut[]; loadAll?: () => Promise<RhRowOut[]> };

export function RhTable({ rows, loadAll }: Props) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin incidencias para capturar en RH.</p>;
  }

  function copy() {
    const all = loadAll ? loadAll() : Promise.resolve(rows);
    copyText(all.then(rhRowsToTsv))
      .then(() => all)
      .then((copied) => toast.success(`Lista copiada (${copied.length} filas)`))
      .catch(() => toast.error("No se pudo copiar la lista; intenta de nuevo"));
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-end gap-3">
        {loadAll && (
          <span className="text-xs text-muted-foreground">
            Copia todas las filas del filtro, no solo esta página.
          </span>
        )}
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
