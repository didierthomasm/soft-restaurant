import { IncidentsView } from "@/components/attendance/incidents-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string; hasta?: string }> };

export default async function IncidenciasPage({ searchParams }: Props) {
  const { desde, hasta } = await searchParams;
  const valid = isIsoDate(desde) && isIsoDate(hasta);
  return <IncidentsView from={valid ? desde : null} to={valid ? hasta : null} />;
}
