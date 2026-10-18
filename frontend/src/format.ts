// Display helpers. Times are shown in the browser's local time zone.

const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

/** 3725 -> "1 h 2 min" */
export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours} h ${minutes} min` : `${minutes} min`;
}

/** 966.6 -> "967 mi" */
export function formatMiles(miles: number): string {
  return `${numberFormat.format(miles)} mi`;
}

/** ISO string or Date -> "Sun, Oct 18, 3:51 PM" */
export function formatDateTime(value: string | Date): string {
  return dateTimeFormat.format(typeof value === 'string' ? new Date(value) : value);
}

export function formatPounds(pounds: number): string {
  return `${numberFormat.format(pounds)} lb`;
}

/** A Date as the "YYYY-MM-DDTHH:mm" local string an <input type="datetime-local"> expects. */
export function toDateTimeLocalValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** The next full hour from now, e.g. 14:20 -> 15:00. */
export function nextFullHour(now = new Date()): Date {
  const next = new Date(now);
  next.setHours(next.getHours() + 1, 0, 0, 0);
  return next;
}
