import { CalendarMonthView } from "@/components/attendance/calendar-month-view";
import { WeekView } from "@/components/attendance/week-view";
import { parseFocus } from "@/lib/calendar";
import { isIsoDate, isIsoMonth } from "@/lib/dates";

type Props = {
  searchParams: Promise<{ vista?: string; desde?: string; mes?: string; empleado?: string; dia?: string }>;
};

export default async function CalendarioPage({ searchParams }: Props) {
  const { vista, desde, mes, empleado, dia } = await searchParams;
  if (vista === "mes") return <CalendarMonthView month={isIsoMonth(mes) ? mes : null} />;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />;
}
