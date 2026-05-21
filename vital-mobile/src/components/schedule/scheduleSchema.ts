/**
 * Zod schemas for schedule JSON that round-trips through the backend's
 * Pydantic schedule discriminated union without loss.
 *
 * Source of truth: kyros-backend/app/wellness/schemas/schedule.py
 */
import { z } from 'zod';

const timeRegex = /^\d{2}:\d{2}$/;

const timeStr = z
  .string()
  .regex(timeRegex, 'Time must be in HH:mm format');

export const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type DayKey = (typeof DAY_KEYS)[number];
export const ALL_DAYS: DayKey[] = [...DAY_KEYS];

const dayEnum = z.enum(DAY_KEYS);

export const activeWindowSchema = z
  .object({
    start: timeStr,
    end: timeStr,
  })
  .refine(({ start, end }) => end > start, {
    message: 'End time must be after start time',
    path: ['end'],
  });

export const recurringScheduleSchema = z.object({
  type: z.literal('recurring'),
  times: z.array(timeStr).min(1, 'Add at least one reminder time'),
  days_of_week: z.array(dayEnum).min(1, 'Select at least one day'),
  start_date: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  timezone: z.string().min(1, 'Timezone is required'),
});

export const intervalScheduleSchema = z.object({
  type: z.literal('interval'),
  interval_minutes: z
    .number({ invalid_type_error: 'Must be a number' })
    .int()
    .min(15, 'Minimum interval is 15 minutes')
    .max(1440, 'Maximum interval is 24 hours'),
  active_window: activeWindowSchema,
  days_of_week: z.array(dayEnum).min(1, 'Select at least one day'),
  start_date: z.string().nullable().optional(),
  timezone: z.string().min(1, 'Timezone is required'),
});

export const scheduleSchema = z.discriminatedUnion('type', [
  recurringScheduleSchema,
  intervalScheduleSchema,
]);

export type Schedule = z.infer<typeof scheduleSchema>;
export type RecurringSchedule = z.infer<typeof recurringScheduleSchema>;
export type IntervalSchedule = z.infer<typeof intervalScheduleSchema>;

// ── helpers ───────────────────────────────────────────────────────────────────

export function deviceTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function defaultRecurringSchedule(): RecurringSchedule {
  return {
    type: 'recurring',
    times: ['08:00'],
    days_of_week: [...ALL_DAYS],
    start_date: null,
    end_date: null,
    timezone: deviceTimezone(),
  };
}

export function defaultIntervalSchedule(): IntervalSchedule {
  return {
    type: 'interval',
    interval_minutes: 120,
    active_window: { start: '08:00', end: '22:00' },
    days_of_week: [...ALL_DAYS],
    start_date: null,
    timezone: deviceTimezone(),
  };
}
