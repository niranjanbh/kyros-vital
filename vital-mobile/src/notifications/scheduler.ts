/**
 * Notification scheduler — diffs upcoming API fires against locally
 * scheduled notifications and keeps them in sync.
 *
 * Identifiers: every local notification uses fire_key as its identifier so
 * the diff is O(n) set membership checks.
 */
import { getApiClient } from '../api/client';
import { categoryIdForApiCategory } from './categories';
import { getPermissionStatus } from './permissions';

let Notifications: any = null;
try { Notifications = require('expo-notifications'); } catch { /* Expo Go Android */ }

const HORIZON_HOURS = 72;

/** Cached device timezone — used to detect zone changes between syncs. */
let _lastTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

/**
 * Fetches /reminders/upcoming?hours=72, diffs against locally scheduled
 * notifications, cancels stale ones, and schedules new ones.
 *
 * If permission is not granted, exits immediately without scheduling.
 * If timezone changed since last sync, cancels all first to force reschedule.
 */
export async function sync(): Promise<void> {
  if (!Notifications) return;
  const permStatus = await getPermissionStatus();
  if (permStatus !== 'granted') return;

  // Detect timezone change → cancel all and let the diff reschedule
  const currentTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (currentTz !== _lastTimezone) {
    _lastTimezone = currentTz;
    await Notifications.cancelAllScheduledNotificationsAsync();
  }

  // Fetch upcoming fires from API
  let fires: any[] = [];
  try {
    const client = await getApiClient();
    const { data, error } = await client.GET('/v1/wellness/reminders/upcoming', {
      params: { query: { hours: HORIZON_HOURS } },
    });
    if (error) return; // Network error — keep existing notifications
    fires = (data as any[]) ?? [];
  } catch {
    return; // Don't wipe existing notifications on transient errors
  }

  // Build upcoming set
  const now = Date.now();
  const upcomingKeys = new Set(
    fires
      .filter((f) => new Date(f.fire_at).getTime() > now)
      .map((f) => f.fire_key as string)
  );

  // Get currently scheduled notifications
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  const scheduledKeySet = new Set(scheduled.map((n) => n.identifier));

  // 1. Cancel notifications that are no longer in the upcoming window
  const cancelPromises: Promise<void>[] = [];
  for (const n of scheduled) {
    if (!upcomingKeys.has(n.identifier)) {
      cancelPromises.push(
        Notifications.cancelScheduledNotificationAsync(n.identifier)
      );
    }
  }
  await Promise.allSettled(cancelPromises);

  // 2. Schedule fires that aren't already scheduled
  const schedulePromises: Promise<string>[] = [];
  for (const fire of fires) {
    const fireTime = new Date(fire.fire_at).getTime();
    if (fireTime <= now) continue; // Already past
    if (scheduledKeySet.has(fire.fire_key)) continue; // Already scheduled

    const payload = fire.payload as {
      title: string;
      body: string;
      category: string;
      actions: string[];
    };

    schedulePromises.push(
      Notifications.scheduleNotificationAsync({
        identifier: fire.fire_key,
        content: {
          title: payload.title,
          body: payload.body,
          data: {
            fire_key: fire.fire_key,
            tracked_item_id: fire.tracked_item_id,
            reminder_id: fire.reminder_id,
            category: payload.category,
            actions: payload.actions,
          },
          categoryIdentifier: categoryIdForApiCategory(payload.category),
          sound: true,
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.DATE,
          date: new Date(fire.fire_at),
        },
      })
    );
  }

  await Promise.allSettled(schedulePromises);
}

/** Cancel all locally scheduled notifications (e.g. on sign-out). */
export async function cancelAll(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}
