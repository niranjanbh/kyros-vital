import React, { useMemo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { tokens } from '../../theme/tokens';
import { Text } from '../Text';
import { Input } from '../Input';
import { TimePicker } from '../TimePicker';
import { DayOfWeekPicker } from '../DayOfWeekPicker';
import { FormField } from '../FormField';
import type { IntervalSchedule, DayKey } from './scheduleSchema';

const PRESETS: { label: string; minutes: number }[] = [
  { label: '30 min', minutes: 30 },
  { label: '1h', minutes: 60 },
  { label: '1.5h', minutes: 90 },
  { label: '2h', minutes: 120 },
  { label: '3h', minutes: 180 },
  { label: '4h', minutes: 240 },
];

interface Props {
  value: IntervalSchedule;
  onChange: (v: IntervalSchedule) => void;
  errors?: {
    interval_minutes?: string;
    days_of_week?: string;
    general?: string;
  };
}

export function IntervalBuilder({ value, onChange, errors }: Props) {
  const emit = (patch: Partial<IntervalSchedule>) => onChange({ ...value, ...patch });

  // Validate active_window inline — computed from value, not state
  const windowError = useMemo(() => {
    const { start, end } = value.active_window ?? {};
    if (start && end && end <= start) {
      return 'End time must be after start time';
    }
    return null;
  }, [value.active_window]);

  return (
    <View style={styles.container}>
      {/* Interval minutes + quick presets */}
      <FormField
        label="Interval"
        hint="How often to remind you during the active window"
        error={errors?.interval_minutes}
      >
        <Input
          value={String(value.interval_minutes)}
          onChangeText={(t) => {
            const n = parseInt(t, 10);
            if (!isNaN(n)) emit({ interval_minutes: n });
          }}
          keyboardType="numeric"
          placeholder="120"
        />
        {/* Preset chips */}
        <View style={styles.presets}>
          {PRESETS.map((p) => {
            const active = value.interval_minutes === p.minutes;
            return (
              <Pressable
                key={p.minutes}
                style={({ pressed }) => [
                  styles.presetChip,
                  active && styles.presetActive,
                  pressed && { opacity: 0.7 },
                ]}
                onPress={() => emit({ interval_minutes: p.minutes })}
              >
                <Text
                  variant="caption"
                  color={active ? 'ink' : 'slate'}
                  style={active ? { fontFamily: 'GeistSans-Medium' } : undefined}
                >
                  {p.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </FormField>

      {/* Active window */}
      <FormField label="Active Window" error={windowError ?? undefined}>
        <View style={styles.windowRow}>
          <View style={styles.windowField}>
            <Text variant="caption" color="mist" style={styles.windowLabel}>FROM</Text>
            <TimePicker
              value={value.active_window.start}
              onChange={(t) =>
                emit({ active_window: { ...value.active_window, start: t } })
              }
            />
          </View>
          <View style={styles.windowSep}>
            <Text variant="body" color="mist">–</Text>
          </View>
          <View style={styles.windowField}>
            <Text variant="caption" color="mist" style={styles.windowLabel}>TO</Text>
            <TimePicker
              value={value.active_window.end}
              onChange={(t) =>
                emit({ active_window: { ...value.active_window, end: t } })
              }
            />
          </View>
        </View>
      </FormField>

      {/* Days */}
      <FormField label="Active Days" error={errors?.days_of_week}>
        <DayOfWeekPicker
          selected={value.days_of_week as DayKey[]}
          onChange={(days) => emit({ days_of_week: days })}
        />
      </FormField>

      {errors?.general && (
        <Text variant="caption" color="critical">{errors.general}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s24 },
  presets: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: tokens.s8,
    marginTop: tokens.s8,
  },
  presetChip: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: tokens.s4,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  presetActive: {
    borderColor: tokens.ink,
    backgroundColor: tokens.divider,
  },
  windowRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: tokens.s8,
  },
  windowField: { flex: 1, gap: tokens.s4 },
  windowLabel: { letterSpacing: 0.8 },
  windowSep: {
    paddingBottom: tokens.s12,
    paddingHorizontal: tokens.s4,
  },
});
