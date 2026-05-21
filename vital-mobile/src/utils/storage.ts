import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// expo-secure-store is native-only; fall back to localStorage on web
export const storage = {
  getItem: (key: string): Promise<string | null> =>
    Platform.OS === 'web'
      ? Promise.resolve(localStorage.getItem(key))
      : SecureStore.getItemAsync(key),

  setItem: (key: string, value: string): Promise<void> =>
    Platform.OS === 'web'
      ? Promise.resolve(void localStorage.setItem(key, value))
      : SecureStore.setItemAsync(key, value),

  deleteItem: (key: string): Promise<void> =>
    Platform.OS === 'web'
      ? Promise.resolve(void localStorage.removeItem(key))
      : SecureStore.deleteItemAsync(key),
};
