import React, { useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { format } from 'date-fns';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface DateInputProps {
  value: Date;
  onChange: (date: Date) => void;
  mode?: 'date' | 'datetime';
  maximumDate?: Date;
  minimumDate?: Date;
  label?: string;
}

export function DateInput({ value, onChange, mode = 'date', maximumDate, minimumDate, label }: DateInputProps) {
  const [showNativePicker, setShowNativePicker] = useState(false);
  const displayStr = mode === 'datetime'
    ? format(value, "d MMM yyyy 'at' HH:mm")
    : format(value, 'd MMM yyyy');

  if (Platform.OS === 'web') {
    // On web, use native HTML input
    const inputType = mode === 'datetime' ? 'datetime-local' : 'date';
    const webValue = mode === 'datetime'
      ? format(value, "yyyy-MM-dd'T'HH:mm")
      : format(value, 'yyyy-MM-dd');
    const maxVal = maximumDate
      ? (mode === 'datetime' ? format(maximumDate, "yyyy-MM-dd'T'HH:mm") : format(maximumDate, 'yyyy-MM-dd'))
      : undefined;
    const minVal = minimumDate
      ? (mode === 'datetime' ? format(minimumDate, "yyyy-MM-dd'T'HH:mm") : format(minimumDate, 'yyyy-MM-dd'))
      : undefined;

    return (
      <View>
        {label && <Text variant="caption" color="mist" style={styles.label}>{label}</Text>}
        {/* @ts-ignore — web-only input element */}
        <input
          type={inputType}
          value={webValue}
          max={maxVal}
          min={minVal}
          onChange={(e: any) => {
            const raw = e.target.value;
            if (!raw) return;
            const parsed = new Date(raw);
            if (!isNaN(parsed.getTime())) onChange(parsed);
          }}
          style={{
            border: `1px solid ${tokens.hairline}`,
            borderRadius: tokens.radii.card,
            padding: '10px 12px',
            fontFamily: 'GeistSans-Regular, sans-serif',
            fontSize: 15,
            color: tokens.ink,
            backgroundColor: tokens.paper,
            outline: 'none',
            cursor: 'pointer',
            width: '100%',
            boxSizing: 'border-box',
          }}
        />
      </View>
    );
  }

  // Native: DateTimePicker
  // Lazy-require to avoid loading native module in test/web environments
  const DateTimePicker = require('@react-native-community/datetimepicker').default;

  return (
    <View>
      {label && <Text variant="caption" color="mist" style={styles.label}>{label}</Text>}
      <Pressable style={styles.btn} onPress={() => setShowNativePicker(true)}>
        <Text variant="body" color="ink">{displayStr}</Text>
      </Pressable>
      {showNativePicker && (
        <DateTimePicker
          mode={mode}
          value={value}
          display="spinner"
          maximumDate={maximumDate}
          minimumDate={minimumDate}
          onChange={(_: any, date?: Date) => {
            setShowNativePicker(false);
            if (date) onChange(date);
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { marginBottom: tokens.s4, textTransform: 'uppercase', letterSpacing: 0.8 },
  btn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
  },
});
