import { Pressable, StyleSheet, View } from 'react-native';
import { ChevronRight } from 'lucide-react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface ListItemProps {
  title: string;
  subtitle?: string;
  left?: React.ReactNode;
  right?: React.ReactNode;
  showChevron?: boolean;
  onPress?: () => void;
}

export function ListItem({ title, subtitle, left, right, showChevron = true, onPress }: ListItemProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.container, pressed && styles.pressed]}
    >
      {left && <View style={styles.left}>{left}</View>}
      <View style={styles.center}>
        <Text variant="body" color="ink">{title}</Text>
        {subtitle ? <Text variant="bodySmall" color="slate">{subtitle}</Text> : null}
      </View>
      <View style={styles.right}>
        {right}
        {showChevron && <ChevronRight size={16} color={tokens.mist} strokeWidth={1.5} />}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: tokens.s12,
    paddingHorizontal: tokens.s16,
    backgroundColor: tokens.paper,
  },
  pressed: { opacity: 0.7 },
  left: { marginRight: tokens.s12 },
  center: { flex: 1 },
  right: { flexDirection: 'row', alignItems: 'center', gap: tokens.s8 },
});
