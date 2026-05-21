import createClient from 'openapi-fetch';
import type { paths } from './generated/schema';
import { storage } from '../utils/storage';

const DEVICE_ID_KEY = 'vital_device_id';

async function getOrCreateDeviceId(): Promise<string> {
  const devOverride = process.env.EXPO_PUBLIC_DEV_DEVICE_ID;
  if (devOverride) return devOverride;

  let id = await storage.getItem(DEVICE_ID_KEY);
  if (!id) {
    const bytes = new Uint8Array(16);
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
    id = `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    await storage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function getApiClient() {
  const deviceId = await getOrCreateDeviceId();
  return createClient<paths>({
    baseUrl: BASE_URL,
    headers: {
      'X-Device-Id': deviceId,
      'Content-Type': 'application/json',
    },
  });
}

export function createApiClient(deviceId: string) {
  return createClient<paths>({
    baseUrl: BASE_URL,
    headers: {
      'X-Device-Id': deviceId,
      'Content-Type': 'application/json',
    },
  });
}

export { getOrCreateDeviceId };
