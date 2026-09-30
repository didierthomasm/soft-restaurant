import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RhType, SummaryOut } from "@/lib/api/types";
import { RH_LABELS } from "@/lib/labels";

type Props = { summaries: SummaryOut[]; names: Map<number, string> };

function withJustified(total: number, justified: number): string {
  return justified > 0 ? `${total} (${justified} just.)` : String(total);
}

function absenceTypes(byType: SummaryOut["justified_by_type"]): string {
  return Object.entries(byType)
    .map(([type, count]) => `${RH_LABELS[type as RhType]}: ${count}`)
    .join(", ");
}

export function SummaryTable({ summaries, names }: Props) {
  if (summaries.length === 0) return <p className="text-sm text-muted-foreground">Sin datos.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empleado</TableHead>
          <TableHead>Días trabajados</TableHead>
          <TableHead>Retardos</TableHead>
          <TableHead>Faltas</TableHead>
          <TableHead>Ausencias justificadas</TableHead>
          <TableHead>Pendientes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {summaries.map((s) => (
          <TableRow key={`${s.employee_id}-${s.period}`}>
            <TableCell>{names.get(s.employee_id) ?? s.employee_id}</TableCell>
            <TableCell>{s.worked}</TableCell>
            <TableCell>{withJustified(s.late, s.late_justified)}</TableCell>
            <TableCell>{withJustified(s.absent, s.absent_justified)}</TableCell>
            <TableCell>{absenceTypes(s.justified_by_type)}</TableCell>
            <TableCell>{s.unresolved}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
