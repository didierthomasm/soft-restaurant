import { IncidentsView } from "@/components/attendance/incidents-view";
import { parseIncidentQuery, type UrlParams } from "@/lib/incident-query";

type Props = { searchParams: Promise<UrlParams> };

export default async function IncidenciasPage({ searchParams }: Props) {
  return <IncidentsView query={parseIncidentQuery(await searchParams)} />;
}
