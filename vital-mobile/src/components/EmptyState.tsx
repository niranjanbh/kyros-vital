import { StyleSheet, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  body?: string;
  cta?: { label: string; onPress: () => void };
}

export function EmptyState({ title, body, cta }: EmptyStateProps) {
  return (
    <View style={styles.container}>
      <Text variant="h2" color="ink" style={styles.title}>{title}</Text>
      {body ? <Text variant="body" color="slate" style={styles.body}>{body}</Text> : null}
      {cta ? <Button onPress={cta.onPress} variant="secondary" style={styles.cta}>{cta.label}</Button> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.s32,
  },
  title: { textAlign: 'center', marginBottom: tokens.s8 },
  body: { textAlign: 'center', marginBottom: tokens.s24 },
  cta: { minWidth: 160 },
});
