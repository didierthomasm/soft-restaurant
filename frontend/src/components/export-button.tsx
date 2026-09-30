import { Button } from "@/components/ui/button";

type Props = { from: string; to: string; group: "week" | "month" };

/** `group` sets how the workbook's summary sheet is grouped (backend default: week). */
export function ExportButton({ from, to, group }: Props) {
  const query = new URLSearchParams({ from, to, group }).toString();
  return (
    <Button asChild variant="outline">
      <a href={`/backend/attendance/export.xlsx?${query}`} download>
        Exportar a Excel
      </a>
    </Button>
  );
}
