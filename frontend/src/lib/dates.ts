/** Dates as local "YYYY-MM-DD" strings, matching the backend's naive local dates. */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 86_400_000;
const WEEKDAY_SHORT = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

const pad = (value: number) => String(value).padStart(2, "0");

export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function isIsoDate(value: string | undefined | null): value is string {
  return !!value && ISO_DATE.test(value) && toIsoDate(parseIsoDate(value)) === value;
}

export function todayIso(now: Date = new Date()): string {
  return toIsoDate(now);
}

export function addDays(value: string, days: number): string {
  const date = parseIsoDate(value);
  return toIsoDate(new Date(date.getFullYear(), date.getMonth(), date.getDate() + days));
}

export function weekStart(value: string): string {
  const mondayOffset = (parseIsoDate(value).getDay() + 6) % 7;
  return addDays(value, -mondayOffset);
}

export function monthRange(value: string): { from: string; to: string } {
  const date = parseIsoDate(value);
  return {
    from: toIsoDate(new Date(date.getFullYear(), date.getMonth(), 1)),
    to: toIsoDate(new Date(date.getFullYear(), date.getMonth() + 1, 0)),
  };
}

export function daysBetween(from: string, to: string): string[] {
  const count = Math.round((parseIsoDate(to).getTime() - parseIsoDate(from).getTime()) / DAY_MS);
  return Array.from({ length: Math.max(count + 1, 0) }, (_, offset) => addDays(from, offset));
}

export function isoWeekNumber(value: string): number {
  const date = parseIsoDate(value);
  const thursday = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + 3 - ((date.getDay() + 6) % 7),
  );
  const yearStart = new Date(thursday.getFullYear(), 0, 1);
  return Math.floor(Math.round((thursday.getTime() - yearStart.getTime()) / DAY_MS) / 7) + 1;
}

export function formatDay(value: string): string {
  const date = parseIsoDate(value);
  return `${WEEKDAY_SHORT[date.getDay()]} ${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;
}

export function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export function formatTime(datetime: string | null | undefined): string {
  return datetime ? datetime.slice(11, 16) : "";
}

/** Year the ISO week belongs to (the year of its Thursday): 2027-01-01 is 2026-W53. */
export function isoWeekYear(value: string): number {
  const date = parseIsoDate(value);
  const thursday = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + 3 - ((date.getDay() + 6) % 7),
  );
  return thursday.getFullYear();
}

/** Monday of ISO week `week` of `year` (week 1 contains January 4th). */
export function isoWeekMonday(year: number, week: number): string {
  const january4 = toIsoDate(new Date(year, 0, 4));
  return addDays(weekStart(january4), (week - 1) * 7);
}

/** "YYYY-MM-DDTHH:MM…" (naive business time from the backend) → "DD/MM/YYYY HH:MM". */
export function formatDateTime(datetime: string | null | undefined): string {
  return datetime ? `${formatDate(datetime.slice(0, 10))} ${formatTime(datetime)}` : "";
}
