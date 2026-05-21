/**
 * ScheduleBuilder — top-level reusable schedule editor.
 *
 * Emits schedule JSON that round-trips through scheduleSchema.parse()
 * without loss. Validates on every change and surfaces inline errors.
 */
import React, { useCallback, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';

import { tokens } from '../../theme/tokens';
import { Text } from '../Text';
import { SegmentedControl } from '../SegmentedControl';
import { RecurringBuilder } from './RecurringBuilder';
import { IntervalBuilder } from './IntervalBuilder';
import {
  scheduleSchema,
  defaultIntervalSchedule,
  defaultRecurringSchedule,
  deviceTimezone,
  type Schedule,
  type RecurringSchedule,
  type IntervalSchedule,
} from './scheduleSchema';

interface ScheduleBuilderProps {
  value: Record<string, unknown>;
  onChange: (schedule: Record<string, unknown>) => void;
  /** External error injected by the parent form on submit */
  error?: string;
}

const MODE_OPTIONS = [
  { value: 'recurring', label: 'At specific times' },
  { value: 'interval', label: 'Every few hours' },
] as const;

type Mode = (typeof MODE_OPTIONS)[number]['value'];

/** Extract flat field errors from a Zod SafeParseError result. */
function extractErrors(result: ReturnType<typeof scheduleSchema.safeParse>) {
  if (result.success) return {};
  const flat: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = issue.path.join('.');
    if (!flat[key]) flat[key] = issue.message;
  }
  return flat;
}

export function ScheduleBuilder({ value, onChange, error }: ScheduleBuilderProps) {
  const mode: Mode =
    (value?.type as Mode) === 'interval' ? 'interval' : 'recurring';

  // Inline validation — recomputed on every value change
  const validationErrors = useMemo(() => {
    const result = scheduleSchema.safeParse(value);
    return extractErrors(result);
  }, [value]);

  const handleModeChange = useCallback(
    (newMode: string) => {
      if (newMode === mode) return;
      const next =
        newMode === 'interval'
          ? defaultIntervalSchedule()
          : defaultRecurringSchedule();
      onChange(next as Record<string, unknown>);
    },
    [mode, onChange]
  );

  const handleRecurringChange = useCallback(
    (v: RecurringSchedule) => {
      onChange({ ...v, timezone: v.timezone || deviceTimezone() } as Record<string, unknown>);
    },
    [onChange]
  );

  const handleIntervalChange = useCallback(
    (v: IntervalSchedule) => {
      onChange({ ...v, timezone: v.timezone || deviceTimezone() } as Record<string, unknown>);
    },
    [onChange]
  );

  const recurringErrors = {
    times: validationErrors['times'] ?? validationErrors['times.0'],
    days_of_week: validationErrors['days_of_week'],
  };

  const intervalErrors = {
    interval_minutes: validationErrors['interval_minutes'],
    days_of_week: validationErrors['days_of_week'],
    general: validationErrors['active_window'] ?? validationErrors['active_window.end'],
  };

  return (
    <View style={styles.container}>
      {/* Mode selector */}
      <SegmentedControl
        options={[...MODE_OPTIONS]}
        value={mode}
        onChange={handleModeChange}
      />

      {/* Sub-builder */}
      <View style={styles.builder}>
        {mode === 'recurring' ? (
          <RecurringBuilder
            value={value as unknown as RecurringSchedule}
            onChange={handleRecurringChange}
            errors={recurringErrors}
          />
        ) : (
          <IntervalBuilder
            value={value as unknown as IntervalSchedule}
            onChange={handleIntervalChange}
            errors={intervalErrors}
          />
        )}
      </View>

      {/* External error from parent form submit */}
      {error && (
        <Text variant="caption" color="critical" style={styles.externalError}>
          {error}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s16 },
  builder: { gap: tokens.s24 },
  externalError: { marginTop: tokens.s4 },
});
