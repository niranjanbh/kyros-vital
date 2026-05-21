import { useEffect } from 'react';
import { AppState } from 'react-native';
import { useQueryClient } from '@tanstack/react-query';
import { sync } from '../notifications/scheduler';

let cancelAllScheduledNotificationsAsync: (() => Promise<void>) | null = null;
try {
  cancelAllScheduledNotificationsAsync =
    require('expo-notifications').cancelAllScheduledNotificationsAsync;
} catch {
  // expo-notifications unavailable in Expo Go on Android
}

let _lastTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

/**
 * Runs notification sync:
 *  - Once on mount (initial schedule population)
 *  - On every foreground event (AppState → active)
 *  - When tracked-items or reminder queries are updated in the TanStack cache
 *  - On timezone change: cancels all existing notifications before re-syncing
 *
 * Add this hook once in the root layout so it covers all navigation stacks.
 */
export function useNotificationSync(): void {
  const qc = useQueryClient();

  useEffect(() => {
    // Initial sync
    sync().catch(() => {});

    // Foreground sync
    const appStateSub = AppState.addEventListener('change', async (nextState) => {
      if (nextState !== 'active') return;

      const currentTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (currentTz !== _lastTimezone) {
        _lastTimezone = currentTz;
        // Timezone changed → cancel all and let sync() reschedule
        await cancelAllScheduledNotificationsAsync?.().catch(() => {});
      }

      sync().catch(() => {});
    });

    // Re-sync after tracked-item or reminder mutations settle
    const cacheUnsub = qc.getQueryCache().subscribe((event) => {
      if (event.type !== 'updated') return;
      const key = String(event.query.queryKey[0] ?? '');
      if (key === 'tracked-items' || key === 'tracked-item' || key === 'upcoming-reminders') {
        sync().catch(() => {});
      }
    });

    return () => {
      appStateSub.remove();
      cacheUnsub();
    };
  }, [qc]);
}
