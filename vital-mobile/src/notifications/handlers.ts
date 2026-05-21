/**
 * Notification response handlers.
 *
 * Registers a listener for notification action responses:
 *  - taken / skipped / logged_value / acknowledged → POST /logs with fire_key
 *  - snooze_15 → schedule a local notification 15 minutes out (no API call)
 *  - DEFAULT (bare notification tap) → open the app, no log entry
 */
import { getApiClient } from '../api/client';

let Notifications: any = null;
try { Notifications = require('expo-notifications'); } catch { /* Expo Go Android */ }

const ACTION_TO_API: Record<string, string | null> = {
  taken:        'taken',
  skipped:      'skipped',
  snooze_15:    null, // handled locally, no API call
  logged_value: 'logged_value',
  acknowledged: 'acknowledged',
};

async function handleSnooze(
  originalRequest: Notifications.NotificationRequest
): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    // Unique identifier so it doesn't conflict with the original fire_key
    identifier: `snooze-${originalRequest.identifier}-${Date.now()}`,
    content: originalRequest.content,
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
      seconds: 15 * 60,
      repeats: false,
    },
  });
}

async function handleLogAction(
  actionId: string,
  data: Record<string, unknown>
): Promise<void> {
  const fireKey = data.fire_key as string | undefined;
  const trackedItemId = data.tracked_item_id as string | undefined;

  if (!fireKey || !trackedItemId) return;

  const apiAction = ACTION_TO_API[actionId];
  if (!apiAction) return;

  try {
    const client = await getApiClient();
    await client.POST('/v1/wellness/logs/', {
      body: {
        tracked_item_id: trackedItemId,
        action: apiAction,
        occurred_at: new Date().toISOString(),
        fire_key: fireKey,
      } as any,
    });
  } catch {
    // Best-effort: if the app is killed and comes back, the user can
    // manually log the action from the Today screen.
  }
}

/**
 * Registers the notification response listener.
 * Returns an unsubscribe function — call it on unmount / sign-out.
 */
export function registerNotificationHandlers(): () => void {
  if (!Notifications) return () => {};
  const subscription = Notifications.addNotificationResponseReceivedListener(
    async (response) => {
      const { actionIdentifier, notification } = response;
      const data = (notification.request.content.data ?? {}) as Record<string, unknown>;

      if (actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER) {
        // Bare tap → open the app, no log entry needed
        return;
      }

      if (actionIdentifier === 'snooze_15') {
        await handleSnooze(notification.request);
        return;
      }

      await handleLogAction(actionIdentifier, data);
    }
  );

  return () => subscription.remove();
}
