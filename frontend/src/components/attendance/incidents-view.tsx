"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { fetchAllRhRows, useIncidents, useRhRows } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { addDays, weekStart } from "@/lib/dates";
import {
  type IncidentQuery,
  incidentQueryString,
  toApiParams,
  withFilters,
} from "@/lib/incident-query";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { IncidentFilters } from "./incident-filters";
import { IncidentTable } from "./incident-table";
import { RhTable } from "./rh-table";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

export function IncidentsView({ query }: { query: IncidentQuery | null }) {
  const buildQuery = useCallback((today: string) => {
    const start = weekStart(today);
    return `desde=${start}&hasta=${addDays(start, 6)}`;
  }, []);
  useEnsurePeriod(query ? query.from : null, buildQuery);
  if (!query) return <Loading />;
  return <Incidents query={query} />;
}

function Incidents({ query }: { query: IncidentQuery }) {
  const router = useRouter();
  const go = (next: IncidentQuery) =>
    router.push(`/incidencias?${incidentQueryString(next)}`, { scroll: false });
  const incidents = useIncidents(toApiParams(query, query.page));
  const rhRows = useRhRows(toApiParams(query, query.rhPage));
  const employees = useEmployees();
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const byId = new Map<number, EmployeeRef>((employees.data ?? []).map((e) => [e.id, e]));
  const select = (day: DayOut) => {
    const employee = byId.get(day.employee_id);
    if (employee) setSelection({ day, employee });
  };
  const unresolved = incidents.data?.data.unresolved ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <IncidentFilters
          key={incidentQueryString(query)}
          query={query}
          employees={(employees.data ?? []).filter((e) => e.active)}
          onApply={go}
        />
        <ExportButton from={query.from} to={query.to} group="week" />
      </div>
      {incidents.data && <WarningsList warnings={incidents.data.data.warnings} />}
      {unresolved > 0 && (
        <p role="status" className="flex items-center gap-2 text-sm">
          {unresolved} {unresolved === 1 ? "cambio sin registrar" : "cambios sin registrar"}
          <Button
            size="sm"
            variant="link"
            onClick={() => go(withFilters(query, { types: ["UNREGISTERED_CHANGE"], status: "all" }))}
          >
            Ver
          </Button>
        </p>
      )}
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Para capturar en RH</h2>
        {rhRows.isPending && <Loading />}
        {rhRows.isError && <QueryError error={rhRows.error} onRetry={() => rhRows.refetch()} />}
        {rhRows.data && (
          <>
            <RhTable rows={rhRows.data.data.items} loadAll={() => fetchAllRhRows(query)} />
            <Pagination
              meta={rhRows.data.page}
              label="Páginas de RH"
              onPage={(rhPage) => go({ ...query, rhPage })}
            />
          </>
        )}
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Todas las incidencias</h2>
        {incidents.isPending && <Loading />}
        {incidents.isError && <QueryError error={incidents.error} onRetry={() => incidents.refetch()} />}
        {incidents.data && (
          <>
            <IncidentTable days={incidents.data.data.items} byId={byId} onSelect={select} />
            <Pagination
              meta={incidents.data.page}
              label="Páginas de incidencias"
              onPage={(page) => go({ ...query, page })}
            />
          </>
        )}
      </section>
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
