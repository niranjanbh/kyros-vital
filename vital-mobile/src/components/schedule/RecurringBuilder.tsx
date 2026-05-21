import React, { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { Plus, Trash2 } from 'lucide-react-native';
import { format } from 'date-fns';
import DateTimePicker from '@react-native-community/datetimepicker';

import { tokens } from '../../theme/tokens';
import { Text } from '../Text';
import { TimePicker } from '../TimePicker';
import { DayOfWeekPicker } from '../DayOfWeekPicker';
import { Toggle } from '../Toggle';
import { FormField } from '../FormField';
import type { RecurringSchedule, DayKey } from './scheduleSchema';

interface Props {
  value: RecurringSchedule;
  onChange: (v: RecurringSchedule) => void;
  errors?: {
    times?: string;
    days_of_week?: string;
    general?: string;
  };
}

export function RecurringBuilder({ value, onChange, errors }: Props) {
  const [showEndDate, setShowEndDate] = useState(!!value.end_date);
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);

  const emit = (patch: Partial<RecurringSchedule>) =>
    onChange({ ...value, ...patch });

  const updateTime = (i: number, t: string) => {
    const times = value.times.map((v, j) => (j === i ? t : v));
    emit({ times });
  };
  const addTime = () => emit({ times: [...value.times, '08:00'] });
  const removeTime = (i: number) =>
    emit({ times: value.times.filter((_, j) => j !== i) });

  const startDateLabel = value.start_date
    ? format(new Date(value.start_date), 'd MMM yyyy')
    : 'Today';
  const endDateLabel = value.end_date
    ? format(new Date(value.end_date), 'd MMM yyyy')
    : 'Select date';

  return (
    <View style={styles.container}>
      {/* Times array */}
      <FormField label="Reminder Times" error={errors?.times}>
        <View style={styles.timesList}>
          {value.times.map((t, i) => (
            <View key={i} style={styles.timeRow}>
              <View style={styles.timePicker}>
                <TimePicker value={t} onChange={(v) => updateTime(i, v)} />
              </View>
              {value.times.length > 1 && (
                <Pressable onPress={() => removeTime(i)} hitSlop={8} style={styles.removeBtn}>
                  <Trash2 size={16} color={tokens.critical} strokeWidth={1.5} />
                </Pressable>
              )}
            </View>
          ))}
          {value.times.length < 8 && (
            <Pressable style={styles.addTimeRow} onPress={addTime}>
              <Plus size={14} color={tokens.tealDeep} strokeWidth={2} />
              <Text variant="bodySmall" color="tealDeep">Add time</Text>
            </Pressable>
          )}
        </View>
      </FormField>

      {/* Days */}
      <FormField label="Days" error={errors?.days_of_week}>
        <DayOfWeekPicker
          selected={value.days_of_week as DayKey[]}
          onChange={(days) => emit({ days_of_week: days })}
        />
      </FormField>

      {/* Date range */}
      <FormField label="Start Date">
        <Pressable style={styles.dateBtn} onPress={() => setShowStartPicker(true)}>
          <Text variant="body" color="ink">{startDateLabel}</Text>
        </Pressable>
        {showStartPicker && (
          <DateTimePicker
            mode="date"
            value={value.start_date ? new Date(value.start_date) : new Date()}
            display="spinner"
            onChange={(_, date) => {
              setShowStartPicker(false);
              if (date) emit({ start_date: format(date, 'yyyy-MM-dd') });
            }}
          />
        )}
      </FormField>

      <FormField label="Duration">
        <Toggle
          value={showEndDate}
          onChange={(v) => {
            setShowEndDate(v);
            if (!v) emit({ end_date: null });
          }}
          label="Set an end date"
        />
        {showEndDate && (
          <View style={styles.endDateField}>
            <Pressable style={styles.dateBtn} onPress={() => setShowEndPicker(true)}>
              <Text variant="body" color={value.end_date ? 'ink' : 'mist'}>
                {endDateLabel}
              </Text>
            </Pressable>
            {showEndPicker && (
              <DateTimePicker
                mode="date"
                value={value.end_date ? new Date(value.end_date) : new Date()}
                display="spinner"
                minimumDate={value.start_date ? new Date(value.start_date) : new Date()}
                onChange={(_, date) => {
                  setShowEndPicker(false);
                  if (date) emit({ end_date: format(date, 'yyyy-MM-dd') });
                }}
              />
            )}
          </View>
        )}
      </FormField>

      {errors?.general && (
        <Text variant="caption" color="critical">{errors.general}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s24 },
  timesList: { gap: tokens.s8 },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: tokens.s12 },
  timePicker: { flex: 1 },
  removeBtn: { padding: tokens.s4 },
  addTimeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.s8,
    paddingVertical: tokens.s8,
  },
  dateBtn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
  },
  endDateField: { marginTop: tokens.s8 },
});
