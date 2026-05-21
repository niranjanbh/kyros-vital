import { Platform } from 'react-native';

export type PermissionStatus = 'granted' | 'denied' | 'undetermined';

// expo-notifications remote push support was removed from Expo Go on Android (SDK 53+).
// Wrap the import so the app doesn't crash when running in Expo Go on Android.
let Notifications: any = null;
try {
  Notifications = require('expo-notifications');
} catch {
  // Running in Expo Go on Android — notifications unavailable
}

export async function requestPermissions(): Promise<PermissionStatus> {
  if (!Notifications) return 'denied';

  if (Platform.OS === 'android') {
    const { status } = await Notifications.requestPermissionsAsync();
    return status as PermissionStatus;
  }

  const { status: existing } = await Notifications.getPermissionsAsync();
  if (existing === 'denied') return 'denied';

  const { status } = await Notifications.requestPermissionsAsync({
    ios: {
      allowAlert: true,
      allowBadge: true,
      allowSound: true,
      allowAnnouncements: true,
    },
  });

  return status as PermissionStatus;
}

export async function getPermissionStatus(): Promise<PermissionStatus> {
  if (!Notifications) return 'denied';
  const { status } = await Notifications.getPermissionsAsync();
  return status as PermissionStatus;
}
