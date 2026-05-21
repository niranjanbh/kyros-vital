import { StyleSheet, View, ViewStyle } from 'react-native';
import { tokens } from '../theme/tokens';

interface CardProps {
  children: React.ReactNode;
  elevated?: boolean;
  style?: ViewStyle;
}

export function Card({ children, elevated = false, style }: CardProps) {
  return (
    <View style={[styles.card, elevated && styles.elevated, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    padding: tokens.s16,
  },
  elevated: {
    shadowColor: tokens.ink,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
});
