import { Pressable, StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface NumberStepperProps {
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
}

export function NumberStepper({ value, onChange, min = 1, max = 99 }: NumberStepperProps) {
  return (
    <View style={styles.row}>
      <Pressable
        style={({ pressed }) => [styles.btn, pressed && styles.pressed, value <= min && styles.disabled]}
        onPress={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
      >
        <Text variant="h2" color="ink" style={styles.btnLabel}>−</Text>
      </Pressable>

      <View style={styles.valueBox}>
        <Text variant="body" color="ink" style={styles.value}>{value}</Text>
      </View>

      <Pressable
        style={({ pressed }) => [styles.btn, pressed && styles.pressed, value >= max && styles.disabled]}
        onPress={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
      >
        <Text variant="h2" color="ink" style={styles.btnLabel}>+</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
  btn: {
    paddingHorizontal: tokens.s16,
    paddingVertical: tokens.s8,
    backgroundColor: tokens.paper,
  },
  btnLabel: {
    fontFamily: 'GeistSans-Regular',
    lineHeight: 22,
  },
  pressed: { backgroundColor: tokens.divider },
  disabled: { opacity: 0.35 },
  valueBox: {
    paddingHorizontal: tokens.s24,
    paddingVertical: tokens.s8,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: tokens.hairline,
    minWidth: 56,
    alignItems: 'center',
    backgroundColor: tokens.paper,
  },
  value: { fontFamily: 'GeistSans-Medium' },
});
