import { WeekView } from "@/components/attendance/week-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string; empleado?: string; dia?: string }> };

function parseFocus(empleado: string | undefined, dia: string | undefined) {
  const employeeId = Number(empleado);
  if (!Number.isInteger(employeeId) || employeeId <= 0 || !isIsoDate(dia)) return null;
  return { employeeId, day: dia };
}

export default async function SemanaPage({ searchParams }: Props) {
  const { desde, empleado, dia } = await searchParams;
  return (
    <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />
  );
}
