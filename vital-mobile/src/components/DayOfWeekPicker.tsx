import { Pressable, StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'] as const;
const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type DayKey = typeof DAY_KEYS[number];

interface DayOfWeekPickerProps {
  selected: DayKey[];
  onChange: (days: DayKey[]) => void;
}

export function DayOfWeekPicker({ selected, onChange }: DayOfWeekPickerProps) {
  const toggle = (day: DayKey) => {
    onChange(
      selected.includes(day) ? selected.filter((d) => d !== day) : [...selected, day]
    );
  };

  return (
    <View style={styles.row}>
      {DAY_KEYS.map((day, i) => {
        const isSelected = selected.includes(day);
        return (
          <Pressable
            key={day}
            onPress={() => toggle(day)}
            style={[styles.pill, isSelected ? styles.selectedPill : styles.unselectedPill]}
          >
            <Text
              variant="mono"
              color={isSelected ? 'paper' : 'slate'}
              style={{ fontSize: 12 }}
            >
              {DAYS[i]}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: tokens.s8 },
  pill: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectedPill: { backgroundColor: tokens.ink },
  unselectedPill: { borderWidth: 1, borderColor: tokens.hairline },
});
