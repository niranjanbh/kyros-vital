import React from 'react';
import {
  Modal,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

export interface SheetAction {
  id: string;
  label: string;
  variant?: 'default' | 'destructive' | 'primary';
}

interface ActionSheetProps {
  visible: boolean;
  title?: string;
  subtitle?: string;
  actions: SheetAction[];
  onAction: (actionId: string) => void;
  onClose: () => void;
}

export function ActionSheet({ visible, title, subtitle, actions, onAction, onClose }: ActionSheetProps) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable style={styles.backdrop} onPress={onClose} />
      <View style={styles.sheet}>
        {(title || subtitle) && (
          <View style={styles.header}>
            {title && <Text variant="h2" color="ink">{title}</Text>}
            {subtitle && <Text variant="bodySmall" color="slate" style={styles.subtitleText}>{subtitle}</Text>}
          </View>
        )}

        <View style={styles.actions}>
          {actions.map((action, i) => (
            <React.Fragment key={action.id}>
              {i > 0 && <View style={styles.separator} />}
              <Pressable
                style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}
                onPress={() => onAction(action.id)}
              >
                <Text
                  variant="body"
                  color={action.variant === 'destructive' ? 'critical' : action.variant === 'primary' ? 'tealDeep' : 'ink'}
                  style={action.variant === 'primary' ? { fontFamily: 'GeistSans-Medium' } : undefined}
                >
                  {action.label}
                </Text>
              </Pressable>
            </React.Fragment>
          ))}
        </View>

        <View style={styles.separator} />
        <Pressable
          style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}
          onPress={onClose}
        >
          <Text variant="body" color="mist">Cancel</Text>
        </Pressable>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26,26,26,0.4)',
  },
  sheet: {
    backgroundColor: tokens.paper,
    borderTopLeftRadius: tokens.radii.card * 2,
    borderTopRightRadius: tokens.radii.card * 2,
    paddingBottom: tokens.s32,
    overflow: 'hidden',
  },
  header: {
    paddingHorizontal: tokens.s20,
    paddingVertical: tokens.s16,
    borderBottomWidth: 1,
    borderBottomColor: tokens.hairline,
  },
  subtitleText: {
    marginTop: tokens.s4,
  },
  actions: {},
  actionRow: {
    paddingVertical: tokens.s20,
    paddingHorizontal: tokens.s20,
    alignItems: 'center',
    minHeight: 56,
    justifyContent: 'center',
  },
  pressed: {
    backgroundColor: tokens.divider,
  },
  separator: {
    height: 1,
    backgroundColor: tokens.hairline,
  },
});
