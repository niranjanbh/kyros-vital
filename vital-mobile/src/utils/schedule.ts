/** Human-readable schedule summaries and schedule JSON builders. */

export function formatScheduleSummary(schedule: Record<string, any> | null | undefined): string {
  if (!schedule) return '';

  if (schedule.type === 'recurring') {
    const times: string[] = schedule.times ?? [];
    const days: string[] = schedule.days_of_week ?? [];
    const timeStr = times.join(' and ');
    const dayStr = days.length === 7 ? 'Daily' : `On ${days.join(', ')}`;
    return `${dayStr} at ${timeStr}`;
  }

  if (schedule.type === 'interval') {
    const mins: number = schedule.interval_minutes ?? 60;
    const hours = mins / 60;
    const intervalStr = Number.isInteger(hours) ? `${hours}h` : `${mins} min`;
    const start: string = schedule.active_window?.start ?? '08:00';
    const end: string = schedule.active_window?.end ?? '22:00';
    const days: string[] = schedule.days_of_week ?? [];
    const dayStr = days.length === 7 ? 'every day' : `on ${days.join(', ')}`;
    return `Every ${intervalStr}, ${start}–${end} (${dayStr})`;
  }

  return 'Custom schedule';
}

/** Default spread of reminder times for a given dose count. */
export function defaultTimesForDoses(count: number): string[] {
  const presets: Record<number, string[]> = {
    1: ['08:00'],
    2: ['08:00', '20:00'],
    3: ['08:00', '14:00', '20:00'],
    4: ['08:00', '12:00', '16:00', '20:00'],
    5: ['07:00', '10:00', '13:00', '16:00', '20:00'],
    6: ['07:00', '09:00', '12:00', '14:00', '17:00', '20:00'],
  };
  return presets[count] ?? ['08:00'];
}

const ALL_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type DayKey = (typeof ALL_DAYS)[number];
export const ALL_DAYS_ARRAY: DayKey[] = [...ALL_DAYS];

/** Estimate how many fires a reminder schedule produces in `days` days. */
export function estimateExpectedFires(
  schedule: Record<string, any> | null | undefined,
  days: number
): number {
  if (!schedule) return 0;
  const dayKeys: string[] = schedule.days_of_week ?? ALL_DAYS_ARRAY;
  const activeDaysRatio = dayKeys.length / 7;

  if (schedule.type === 'recurring') {
    const times: string[] = schedule.times ?? [];
    return times.length * activeDaysRatio * days;
  }

  if (schedule.type === 'interval') {
    const mins: number = schedule.interval_minutes ?? 120;
    const start = parseInt((schedule.active_window?.start ?? '08:00').split(':')[0], 10);
    const end = parseInt((schedule.active_window?.end ?? '22:00').split(':')[0], 10);
    const windowHours = Math.max(0, end - start);
    const firesPerDay = Math.floor((windowHours * 60) / mins);
    return firesPerDay * activeDaysRatio * days;
  }

  return 0;
}
