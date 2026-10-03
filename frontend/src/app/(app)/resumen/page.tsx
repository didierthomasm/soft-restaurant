import { SummaryView } from "@/components/attendance/summary-view";
import { isIsoMonth } from "@/lib/dates";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function ResumenPage({ searchParams }: Props) {
  const { mes } = await searchParams;
  return <SummaryView month={isIsoMonth(mes) ? mes : null} />;
}
