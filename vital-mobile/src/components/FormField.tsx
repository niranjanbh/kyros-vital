import React from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

interface FormFieldProps {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
  style?: ViewStyle;
}

export function FormField({ label, error, hint, required, children, style }: FormFieldProps) {
  return (
    <View style={[styles.container, style]}>
      <Text variant="label" color="mist" style={styles.label}>
        {label.toUpperCase()}
        {required && <Text variant="label" color="critical"> *</Text>}
      </Text>
      {children}
      {hint && !error && (
        <Text variant="caption" color="mist" style={styles.hint}>{hint}</Text>
      )}
      {error && (
        <Text variant="caption" color="critical" style={styles.hint}>{error}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.s8 },
  label: { letterSpacing: 0.8 },
  hint: { marginTop: tokens.s4 },
});
