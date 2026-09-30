import type { CalendarOut, DayOut, EmployeeRef } from "@/lib/api/types";
import { daysBetween, formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, OUTCOME_STYLES } from "@/lib/labels";
import { cn } from "@/lib/utils";

export type DaySelection = { day: DayOut; employee: EmployeeRef };

type Props = {
  calendar: CalendarOut;
  onSelect: (day: DayOut, employee: EmployeeRef) => void;
};

export function WeekGrid({ calendar, onSelect }: Props) {
  const dates = daysBetween(calendar.start, calendar.end);
  const byKey = new Map(calendar.days.map((d) => [`${d.employee_id}|${d.day}`, d]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr>
            <th scope="col" className="p-2 text-left font-medium">
              Empleado
            </th>
            {dates.map((date) => (
              <th key={date} scope="col" className="p-2 text-center font-medium">
                {formatDay(date)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calendar.employees.map((employee) => (
            <tr key={employee.id} className="border-t">
              <th scope="row" className="p-2 text-left font-medium">
                {employee.short_name}
              </th>
              {dates.map((date) => {
                const day = byKey.get(`${employee.id}|${date}`);
                return (
                  <td key={date} className="p-1">
                    {day && <DayCell day={day} onClick={() => onSelect(day, employee)} />}
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

function DayCell({ day, onClick }: { day: DayOut; onClick: () => void }) {
  const label = OUTCOME_LABELS[day.outcome];
  const time = formatTime(day.checkin);
  const justified = day.justification_id !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={day.outcome === "FUTURE"}
      aria-label={`${formatDay(day.day)}: ${label}${time ? ` ${time}` : ""}${justified ? " (justificado)" : ""}`}
      className={cn(
        "flex h-14 w-full flex-col items-center justify-center rounded-md text-xs",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default",
        OUTCOME_STYLES[day.outcome],
      )}
    >
      <span className="font-medium">{label}</span>
      {time && <span>{time}</span>}
      {justified && <span className="text-[10px]">Justificado</span>}
    </button>
  );
}
