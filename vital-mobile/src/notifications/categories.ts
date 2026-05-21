/**
 * Registers notification action categories.
 *
 * Category identifiers must not contain ':' or '-' (expo-notifications docs).
 * Maps category names from the API to uppercase identifiers.
 *
 * NOTE: Custom action buttons only work in development builds (expo run:ios /
 * eas build). In Expo Go they are silently ignored.
 */
import { Platform } from 'react-native';

let Notifications: any = null;
try { Notifications = require('expo-notifications'); } catch { /* Expo Go Android */ }

const FOREGROUND = true;
const BACKGROUND = false;

function action(
  identifier: string,
  buttonTitle: string,
  opensApp: boolean,
  isDestructive = false
): Notifications.NotificationAction {
  return {
    identifier,
    buttonTitle,
    options: { opensAppToForeground: opensApp, isDestructive },
  };
}

const CATEGORY_DEFS: Array<{
  id: string;
  actions: Notifications.NotificationAction[];
}> = [
  {
    id: 'MEDICATION',
    actions: [
      action('taken', 'Taken', FOREGROUND),
      action('skipped', 'Skipped', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
  {
    id: 'WATER',
    actions: [
      action('logged_value', 'Logged', BACKGROUND),
      action('skipped', 'Skipped', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
  {
    id: 'WORKOUT',
    actions: [
      action('taken', 'Done', FOREGROUND),
      action('skipped', 'Skip', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
  {
    id: 'MEAL',
    actions: [
      action('acknowledged', 'Done', BACKGROUND),
      action('skipped', 'Skip', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
  {
    id: 'VITAL_CHECK',
    actions: [
      action('acknowledged', 'Checked', BACKGROUND),
      action('skipped', 'Skip', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
  {
    id: 'CUSTOM',
    actions: [
      action('acknowledged', 'Done', BACKGROUND),
      action('skipped', 'Skip', BACKGROUND, true),
      action('snooze_15', 'Snooze 15m', BACKGROUND),
    ],
  },
];

/**
 * Registers all notification categories and (on Android) the reminders
 * channel. Safe to call multiple times — idempotent.
 */
export async function registerNotificationCategories(): Promise<void> {
  if (!Notifications) return;
  // Set the handler for foreground notifications (show alert + play sound)
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });

  // Android: create a high-priority channel for reminders
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('reminders', {
      name: 'Reminders',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#2D5F5D',
    });
  }

  // Register action categories
  for (const { id, actions } of CATEGORY_DEFS) {
    await Notifications.setNotificationCategoryAsync(id, actions);
  }
}

/** Maps an API category string to the notification category identifier. */
export function categoryIdForApiCategory(apiCategory: string): string {
  return apiCategory.toUpperCase().replace(/-/g, '_');
}
