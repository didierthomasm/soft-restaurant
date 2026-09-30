import { MonthView } from "@/components/attendance/month-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function MesPage({ searchParams }: Props) {
  const { mes } = await searchParams;
  return <MonthView month={mes && isIsoDate(`${mes}-01`) ? mes : null} />;
}
