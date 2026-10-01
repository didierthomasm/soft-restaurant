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
