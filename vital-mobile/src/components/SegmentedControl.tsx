import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface Option {
  value: string;
  label: string;
}

interface SegmentedControlProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  scrollable?: boolean;
}

export function SegmentedControl({ options, value, onChange, scrollable }: SegmentedControlProps) {
  const inner = options.map((opt) => {
    const active = opt.value === value;
    return (
      <Pressable
        key={opt.value}
        style={[styles.segment, active && styles.active]}
        onPress={() => onChange(opt.value)}
      >
        <Text
          variant="bodySmall"
          color={active ? 'ink' : 'mist'}
          style={active ? { fontFamily: 'GeistSans-Medium' } : undefined}
        >
          {opt.label}
        </Text>
      </Pressable>
    );
  });

  if (scrollable) {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.scroll}>
        <View style={styles.row}>{inner}</View>
      </ScrollView>
    );
  }

  return <View style={styles.row}>{inner}</View>;
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 0 },
  row: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
  segment: {
    paddingVertical: tokens.s8,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  active: {
    backgroundColor: tokens.divider,
  },
});
