import { useEffect, useState } from 'react';
import { AppState } from 'react-native';
import { getPermissionStatus, type PermissionStatus } from '../notifications/permissions';

/**
 * Returns the current notification permission status.
 * Re-checks whenever the app returns to the foreground, so that changes
 * made in OS Settings are reflected without a restart.
 */
export function usePermissionStatus(): PermissionStatus {
  const [status, setStatus] = useState<PermissionStatus>('undetermined');

  useEffect(() => {
    getPermissionStatus().then(setStatus);

    const sub = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        getPermissionStatus().then(setStatus);
      }
    });

    return () => sub.remove();
  }, []);

  return status;
}
