import { StyleSheet, Switch, View } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface ToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}

export function Toggle({ value, onChange, label }: ToggleProps) {
  return (
    <View style={styles.row}>
      {label ? <Text variant="body" color="ink" style={{ flex: 1 }}>{label}</Text> : null}
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ true: tokens.tealDeep, false: tokens.hairline }}
        thumbColor={tokens.paper}
        ios_backgroundColor={tokens.hairline}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: tokens.s4,
  },
});
