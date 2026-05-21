/**
 * Schedule builder tests.
 *
 * Note: The build spec mentions Vitest, but this project uses Jest with
 * jest-expo. The tests are functionally identical — just a different runner.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ThemeProvider } from '../../../theme/ThemeProvider';

// Mock native date picker
jest.mock('@react-native-community/datetimepicker', () => 'DateTimePicker');

import {
  scheduleSchema,
  recurringScheduleSchema,
  intervalScheduleSchema,
} from '../scheduleSchema';
import { IntervalBuilder } from '../IntervalBuilder';
import { RecurringBuilder } from '../RecurringBuilder';
import { ScheduleBuilder } from '../ScheduleBuilder';

function W({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

// ── Schema unit tests (no rendering required) ─────────────────────────────────

describe('scheduleSchema — recurring', () => {
  it('parses "8am and 8pm every day" correctly', () => {
    const input = {
      type: 'recurring' as const,
      times: ['08:00', '20:00'],
      days_of_week: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const,
      timezone: 'Asia/Kolkata',
    };

    const result = recurringScheduleSchema.parse(input);

    expect(result.type).toBe('recurring');
    expect(result.times).toEqual(['08:00', '20:00']);
    expect(result.days_of_week).toHaveLength(7);
    expect(result.timezone).toBe('Asia/Kolkata');
  });

  it('round-trips through parse without loss', () => {
    const input = {
      type: 'recurring' as const,
      times: ['08:00', '13:00', '20:00'],
      days_of_week: ['mon', 'wed', 'fri'] as any,
      start_date: '2026-05-20',
      end_date: '2026-12-31',
      timezone: 'Asia/Kolkata',
    };
    const parsed = recurringScheduleSchema.parse(input);
    const reparsed = recurringScheduleSchema.parse(parsed);
    expect(reparsed).toEqual(parsed);
  });

  it('rejects empty times array', () => {
    expect(() =>
      recurringScheduleSchema.parse({
        type: 'recurring',
        times: [],
        days_of_week: ['mon'],
        timezone: 'UTC',
      })
    ).toThrow();
  });

  it('rejects empty days_of_week', () => {
    expect(() =>
      recurringScheduleSchema.parse({
        type: 'recurring',
        times: ['08:00'],
        days_of_week: [],
        timezone: 'UTC',
      })
    ).toThrow();
  });
});

describe('scheduleSchema — interval', () => {
  it('parses "every 2 hours, 8am–10pm, weekdays only" correctly', () => {
    const input = {
      type: 'interval' as const,
      interval_minutes: 120,
      active_window: { start: '08:00', end: '22:00' },
      days_of_week: ['mon', 'tue', 'wed', 'thu', 'fri'] as any,
      timezone: 'Asia/Kolkata',
    };

    const result = intervalScheduleSchema.parse(input);

    expect(result.type).toBe('interval');
    expect(result.interval_minutes).toBe(120);
    expect(result.active_window.start).toBe('08:00');
    expect(result.active_window.end).toBe('22:00');
    expect(result.days_of_week).toHaveLength(5);
    expect(result.days_of_week).not.toContain('sat');
    expect(result.days_of_week).not.toContain('sun');
  });

  it('round-trips through parse without loss', () => {
    const input = {
      type: 'interval' as const,
      interval_minutes: 90,
      active_window: { start: '09:00', end: '18:00' },
      days_of_week: ['mon', 'tue', 'wed', 'thu', 'fri'] as any,
      timezone: 'Asia/Kolkata',
    };
    const parsed = intervalScheduleSchema.parse(input);
    const reparsed = intervalScheduleSchema.parse(parsed);
    expect(reparsed).toEqual(parsed);
  });

  it('rejects interval below 15 minutes', () => {
    expect(() =>
      intervalScheduleSchema.parse({
        type: 'interval',
        interval_minutes: 10,
        active_window: { start: '08:00', end: '22:00' },
        days_of_week: ['mon'],
        timezone: 'UTC',
      })
    ).toThrow();
  });

  it('rejects active_window where end <= start', () => {
    expect(() =>
      intervalScheduleSchema.parse({
        type: 'interval',
        interval_minutes: 120,
        active_window: { start: '22:00', end: '08:00' },
        days_of_week: ['mon'],
        timezone: 'UTC',
      })
    ).toThrow();
  });

  it('rejects equal start and end times', () => {
    expect(() =>
      intervalScheduleSchema.parse({
        type: 'interval',
        interval_minutes: 60,
        active_window: { start: '12:00', end: '12:00' },
        days_of_week: ['mon'],
        timezone: 'UTC',
      })
    ).toThrow();
  });
});

describe('discriminated union', () => {
  it('dispatches to recurring schema', () => {
    const result = scheduleSchema.parse({
      type: 'recurring',
      times: ['08:00'],
      days_of_week: ['mon'],
      timezone: 'UTC',
    });
    expect(result.type).toBe('recurring');
  });

  it('dispatches to interval schema', () => {
    const result = scheduleSchema.parse({
      type: 'interval',
      interval_minutes: 120,
      active_window: { start: '08:00', end: '22:00' },
      days_of_week: ['mon'],
      timezone: 'UTC',
    });
    expect(result.type).toBe('interval');
  });
});

// ── Component rendering tests ─────────────────────────────────────────────────

describe('IntervalBuilder — invalid active window shows inline error', () => {
  it('shows error message when end time is before start time', () => {
    const { getByText } = render(
      <W>
        <IntervalBuilder
          value={{
            type: 'interval',
            interval_minutes: 120,
            active_window: { start: '22:00', end: '08:00' },
            days_of_week: ['mon'],
            timezone: 'UTC',
          }}
          onChange={jest.fn()}
        />
      </W>
    );

    expect(getByText('End time must be after start time')).toBeTruthy();
  });

  it('shows no error for valid active window', () => {
    const { queryByText } = render(
      <W>
        <IntervalBuilder
          value={{
            type: 'interval',
            interval_minutes: 120,
            active_window: { start: '08:00', end: '22:00' },
            days_of_week: ['mon'],
            timezone: 'UTC',
          }}
          onChange={jest.fn()}
        />
      </W>
    );

    expect(queryByText('End time must be after start time')).toBeNull();
  });

  it('renders preset chips', () => {
    const { getByText } = render(
      <W>
        <IntervalBuilder
          value={{
            type: 'interval',
            interval_minutes: 120,
            active_window: { start: '08:00', end: '22:00' },
            days_of_week: ['mon'],
            timezone: 'UTC',
          }}
          onChange={jest.fn()}
        />
      </W>
    );
    expect(getByText('2h')).toBeTruthy();
    expect(getByText('1h')).toBeTruthy();
  });
});

describe('RecurringBuilder', () => {
  it('renders without crashing', () => {
    const { toJSON } = render(
      <W>
        <RecurringBuilder
          value={{
            type: 'recurring',
            times: ['08:00', '20:00'],
            days_of_week: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
            timezone: 'Asia/Kolkata',
          }}
          onChange={jest.fn()}
        />
      </W>
    );
    expect(toJSON()).toBeTruthy();
  });
});

describe('ScheduleBuilder', () => {
  it('renders in recurring mode by default', () => {
    const { toJSON } = render(
      <W>
        <ScheduleBuilder
          value={{ type: 'recurring', times: ['08:00'], days_of_week: ['mon'], timezone: 'UTC' }}
          onChange={jest.fn()}
        />
      </W>
    );
    expect(toJSON()).toBeTruthy();
  });

  it('renders in interval mode when value.type is interval', () => {
    const { getByText } = render(
      <W>
        <ScheduleBuilder
          value={{
            type: 'interval',
            interval_minutes: 120,
            active_window: { start: '08:00', end: '22:00' },
            days_of_week: ['mon'],
            timezone: 'UTC',
          }}
          onChange={jest.fn()}
        />
      </W>
    );
    expect(getByText('Every few hours')).toBeTruthy();
  });

  it('shows external error prop', () => {
    const { getByText } = render(
      <W>
        <ScheduleBuilder
          value={{ type: 'recurring', times: ['08:00'], days_of_week: ['mon'], timezone: 'UTC' }}
          onChange={jest.fn()}
          error="Schedule is required"
        />
      </W>
    );
    expect(getByText('Schedule is required')).toBeTruthy();
  });
});
