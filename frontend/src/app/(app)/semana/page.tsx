import { WeekView } from "@/components/attendance/week-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string }> };

export default async function SemanaPage({ searchParams }: Props) {
  const { desde } = await searchParams;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} />;
}
