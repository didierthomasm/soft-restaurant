import type { RhRowOut } from "@/lib/api/types";

import { formatDate } from "./dates";
import { RH_LABELS } from "./labels";

const HEADER = ["Nombre", "Fecha", "Tipo", "Comentario"];

const clean = (value: string) => value.replace(/[\t\r\n]+/g, " ").trim();

/** Tab-separated rows: pastes cleanly into a spreadsheet or the HR tool. */
export function rhRowsToTsv(rows: RhRowOut[]): string {
  const lines = rows.map((row) =>
    [clean(row.name), formatDate(row.day), RH_LABELS[row.rh_type], clean(row.comment)].join("\t"),
  );
  return [HEADER.join("\t"), ...lines].join("\n");
}
