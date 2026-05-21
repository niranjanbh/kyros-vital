import { Pressable, StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface NetworkErrorProps {
  visible: boolean;
  message?: string;
  onRetry?: () => void;
}

export function NetworkError({ visible, message = 'No connection', onRetry }: NetworkErrorProps) {
  if (!visible) return null;

  return (
    <View style={styles.banner}>
      <Text variant="bodySmall" style={styles.message} numberOfLines={1}>
        {message}
      </Text>
      {onRetry ? (
        <Pressable onPress={onRetry} hitSlop={8}>
          <Text variant="bodySmall" style={styles.retry}>Retry</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    height: 44,
    backgroundColor: tokens.slate,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.s16,
  },
  message: {
    color: tokens.paper,
    flex: 1,
  },
  retry: {
    color: tokens.paper,
    fontFamily: 'GeistSans-Medium',
  },
});
