import { WeekView } from "@/components/attendance/week-view";
import { parseFocus } from "@/lib/calendar";
import { isIsoDate } from "@/lib/dates";

type Props = {
  searchParams: Promise<{ vista?: string; desde?: string; mes?: string; empleado?: string; dia?: string }>;
};

export default async function CalendarioPage({ searchParams }: Props) {
  const { desde, empleado, dia } = await searchParams;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />;
}
