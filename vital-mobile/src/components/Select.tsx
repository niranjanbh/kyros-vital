import { Pressable, StyleSheet, View, ViewStyle } from 'react-native';
import { ChevronDown } from 'lucide-react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface SelectProps {
  label?: string;
  value?: string;
  placeholder?: string;
  onPress: () => void;
  error?: string;
  containerStyle?: ViewStyle;
}

export function Select({ label, value, placeholder = 'Select…', onPress, error, containerStyle }: SelectProps) {
  return (
    <View style={[styles.container, containerStyle]}>
      {label ? <Text variant="label" color="slate" style={styles.label}>{label}</Text> : null}
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.select, { borderColor: error ? tokens.critical : tokens.hairline }, pressed && { opacity: 0.7 }]}
      >
        <Text variant="body" color={value ? 'ink' : 'mist'}>{value ?? placeholder}</Text>
        <ChevronDown size={16} color={tokens.mist} strokeWidth={1.5} />
      </Pressable>
      {error ? <Text variant="caption" color="critical">{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s4 },
  label: { textTransform: 'uppercase', letterSpacing: 0.8 },
  select: {
    borderWidth: 1,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: tokens.paper,
  },
});
