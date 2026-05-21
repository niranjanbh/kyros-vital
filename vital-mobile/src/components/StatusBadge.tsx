import { StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

type BadgeVariant = 'positive' | 'warning' | 'critical' | 'neutral';

interface StatusBadgeProps {
  label: string;
  variant?: BadgeVariant;
}

const bgMap: Record<BadgeVariant, string> = {
  positive: `${tokens.positive}1A`,
  warning:  `${tokens.warning}1A`,
  critical: `${tokens.critical}1A`,
  neutral:  `${tokens.mist}1A`,
};

const colorMap: Record<BadgeVariant, keyof typeof tokens> = {
  positive: 'positive',
  warning:  'warning',
  critical: 'critical',
  neutral:  'mist',
};

export function StatusBadge({ label, variant = 'neutral' }: StatusBadgeProps) {
  return (
    <View style={[styles.badge, { backgroundColor: bgMap[variant] }]}>
      <Text variant="caption" color={colorMap[variant] as any} style={{ textTransform: 'uppercase', letterSpacing: 0.8 }}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: tokens.s8,
    paddingVertical: tokens.s4,
    borderRadius: tokens.radii.card,
    alignSelf: 'flex-start',
  },
});
