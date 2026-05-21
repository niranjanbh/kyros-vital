/**
 * Notification scheduler unit tests.
 * Mocks expo-notifications and the API client so no actual scheduling happens.
 */

// ── mocks (must be at top, before imports) ────────────────────────────────────

const mockGetAll = jest.fn<Promise<any[]>, []>();
const mockCancel = jest.fn<Promise<void>, [string]>();
const mockSchedule = jest.fn<Promise<string>, [any]>();
const mockCancelAll = jest.fn<Promise<void>, []>();
const mockGetPerms = jest.fn<Promise<{ status: string }>, []>();

jest.mock('expo-notifications', () => ({
  getAllScheduledNotificationsAsync: () => mockGetAll(),
  cancelScheduledNotificationAsync: (id: string) => mockCancel(id),
  scheduleNotificationAsync: (req: any) => mockSchedule(req),
  cancelAllScheduledNotificationsAsync: () => mockCancelAll(),
  getPermissionsAsync: () => mockGetPerms(),
  SchedulableTriggerInputTypes: { DATE: 'date', TIME_INTERVAL: 'timeInterval' },
}));

const mockGetApiClient = jest.fn();
jest.mock('../../api/client', () => ({ getApiClient: () => mockGetApiClient() }));

// Bypass actual SecureStore for permission check
jest.mock('../../notifications/permissions', () => ({
  getPermissionStatus: jest.fn().mockResolvedValue('granted'),
}));

// ── tests ─────────────────────────────────────────────────────────────────────

import { sync } from '../scheduler';

const FUTURE = new Date(Date.now() + 60 * 60 * 1000).toISOString(); // +1h
const PAST   = new Date(Date.now() - 60 * 60 * 1000).toISOString(); // -1h

function makeClient(fires: any[]) {
  return {
    GET: jest.fn().mockResolvedValue({ data: fires, error: null }),
    POST: jest.fn().mockResolvedValue({ data: {}, error: null }),
  };
}

function makeFire(fireKey: string, fireAt: string = FUTURE) {
  return {
    fire_key: fireKey,
    fire_at: fireAt,
    tracked_item_id: 'item-001',
    reminder_id: 'rem-001',
    payload: {
      title: 'Medication',
      body: 'Take Aspirin',
      category: 'medication',
      actions: ['taken', 'skipped', 'snooze_15'],
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetPerms.mockResolvedValue({ status: 'granted' });
  mockGetAll.mockResolvedValue([]);
  mockCancel.mockResolvedValue(undefined);
  mockSchedule.mockResolvedValue('scheduled-id');
  mockCancelAll.mockResolvedValue(undefined);
});

describe('sync() — basic scheduling', () => {
  it('schedules a new fire that is not yet scheduled', async () => {
    mockGetApiClient.mockReturnValue(makeClient([makeFire('key-001')]));
    mockGetAll.mockResolvedValue([]);

    await sync();

    expect(mockSchedule).toHaveBeenCalledTimes(1);
    const req = mockSchedule.mock.calls[0][0];
    expect(req.identifier).toBe('key-001');
    expect(req.content.data.fire_key).toBe('key-001');
    expect(req.trigger.type).toBe('date');
  });

  it('does not reschedule a fire that is already scheduled', async () => {
    mockGetApiClient.mockReturnValue(makeClient([makeFire('key-002')]));
    mockGetAll.mockResolvedValue([{ identifier: 'key-002' }]);

    await sync();

    expect(mockSchedule).not.toHaveBeenCalled();
  });

  it('cancels a scheduled notification no longer in upcoming list', async () => {
    mockGetApiClient.mockReturnValue(makeClient([]));
    mockGetAll.mockResolvedValue([{ identifier: 'stale-key' }]);

    await sync();

    expect(mockCancel).toHaveBeenCalledWith('stale-key');
  });

  it('skips fires that are already in the past', async () => {
    mockGetApiClient.mockReturnValue(makeClient([makeFire('past-key', PAST)]));
    mockGetAll.mockResolvedValue([]);

    await sync();

    expect(mockSchedule).not.toHaveBeenCalled();
  });
});

describe('sync() — diff logic', () => {
  it('schedules new fires and cancels stale ones in the same sync', async () => {
    const fires = [makeFire('new-key'), makeFire('keep-key')];
    mockGetApiClient.mockReturnValue(makeClient(fires));
    mockGetAll.mockResolvedValue([
      { identifier: 'keep-key' },
      { identifier: 'stale-key' },
    ]);

    await sync();

    expect(mockSchedule).toHaveBeenCalledTimes(1);
    expect(mockSchedule.mock.calls[0][0].identifier).toBe('new-key');
    expect(mockCancel).toHaveBeenCalledWith('stale-key');
  });

  it('sets correct categoryIdentifier from payload.category', async () => {
    mockGetApiClient.mockReturnValue(makeClient([makeFire('cat-key')]));
    mockGetAll.mockResolvedValue([]);

    await sync();

    const req = mockSchedule.mock.calls[0][0];
    expect(req.content.categoryIdentifier).toBe('MEDICATION');
  });
});

describe('sync() — permission guard', () => {
  it('exits early when permission is not granted', async () => {
    const { getPermissionStatus } = require('../../notifications/permissions');
    (getPermissionStatus as jest.Mock).mockResolvedValueOnce('denied');

    await sync();

    expect(mockGetApiClient).not.toHaveBeenCalled();
    expect(mockSchedule).not.toHaveBeenCalled();
  });
});

describe('sync() — network resilience', () => {
  it('does not cancel existing notifications on API error', async () => {
    mockGetApiClient.mockReturnValue({
      GET: jest.fn().mockRejectedValue(new Error('Network error')),
    });
    mockGetAll.mockResolvedValue([{ identifier: 'keep-this' }]);

    await sync();

    expect(mockCancel).not.toHaveBeenCalled();
  });
});
