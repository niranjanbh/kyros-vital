import { useState } from 'react';
import { StyleSheet, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerStyle?: ViewStyle;
}

export function Input({ label, error, containerStyle, style, ...props }: InputProps) {
  const [focused, setFocused] = useState(false);

  const borderColor = error ? tokens.critical : focused ? tokens.ink : tokens.hairline;

  return (
    <View style={[styles.container, containerStyle]}>
      {label ? <Text variant="label" color="slate" style={styles.label}>{label}</Text> : null}
      <TextInput
        style={[styles.input, { borderColor }, style as object | undefined]}
        placeholderTextColor={tokens.mist}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        {...props}
      />
      {error ? <Text variant="caption" color="critical" style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s4 },
  label: { textTransform: 'uppercase', letterSpacing: 0.8 },
  input: {
    borderWidth: 1,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    fontFamily: 'GeistSans-Regular',
    fontSize: 15,
    color: tokens.ink,
    backgroundColor: tokens.paper,
  },
  error: { marginTop: tokens.s4 },
});
