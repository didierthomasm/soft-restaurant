import type { CalendarOut, DayOut, EmployeeRef } from "@/lib/api/types";
import { daysBetween, formatDay, formatTime, isWeekend } from "@/lib/dates";
import { OUTCOME_LABELS, OUTCOME_SHORT, dayStyle } from "@/lib/labels";
import { cn } from "@/lib/utils";

type Props = {
  calendar: CalendarOut;
  onSelect: (day: DayOut, employee: EmployeeRef) => void;
};

export function MonthGrid({ calendar, onSelect }: Props) {
  const dates = daysBetween(calendar.start, calendar.end);
  const byKey = new Map(calendar.days.map((d) => [`${d.employee_id}|${d.day}`, d]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[960px] table-fixed text-xs">
        <thead>
          <tr>
            <th scope="col" className="w-28 p-1 text-left font-medium">
              Empleado
            </th>
            {dates.map((date) => (
              <th
                key={date}
                scope="col"
                aria-label={formatDay(date)}
                className={cn("p-1 text-center font-medium", isWeekend(date) && "bg-muted/60")}
              >
                {Number(date.slice(8))}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calendar.employees.map((employee) => (
            <tr key={employee.id} className="border-t">
              <th scope="row" className="truncate p-1 text-left font-medium">
                {employee.short_name}
              </th>
              {dates.map((date) => {
                const day = byKey.get(`${employee.id}|${date}`);
                return (
                  <td key={date} className="p-0.5">
                    {day && <MonthCell day={day} onClick={() => onSelect(day, employee)} />}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function describeDay(day: DayOut): string {
  const time = formatTime(day.checkin);
  const notes = [
    day.justification_id !== null && "justificado",
    day.exception !== null && day.outcome !== "JUSTIFIED" && "excepción",
  ].filter(Boolean);
  const base = `${formatDay(day.day)}: ${OUTCOME_LABELS[day.outcome]}${time ? ` ${time}` : ""}`;
  return notes.length > 0 ? `${base} (${notes.join(", ")})` : base;
}

function MonthCell({ day, onClick }: { day: DayOut; onClick: () => void }) {
  const description = describeDay(day);
  const marked = day.justification_id !== null || (day.exception !== null && day.outcome !== "JUSTIFIED");
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={day.outcome === "FUTURE"}
      title={description}
      aria-label={description}
      className={cn(
        "flex h-9 w-full items-center justify-center rounded text-[11px] font-medium",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default",
        dayStyle(day),
        marked && "ring-1 ring-inset ring-sky-500",
      )}
    >
      {OUTCOME_SHORT[day.outcome]}
    </button>
  );
}
