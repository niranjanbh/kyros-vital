/**
 * Notification handler unit tests.
 * Verifies the correct API action is POSTed for each notification action.
 */

// ── mocks (hoisted before all imports) ───────────────────────────────────────

let responseListener: ((response: any) => Promise<void>) | null = null;

const mockSchedule = jest.fn<Promise<string>, [any]>();
jest.mock('expo-notifications', () => ({
  addNotificationResponseReceivedListener: (cb: any) => {
    responseListener = cb;
    return { remove: jest.fn() };
  },
  scheduleNotificationAsync: (req: any) => mockSchedule(req),
  DEFAULT_ACTION_IDENTIFIER: 'expo.modules.notifications.actions.DEFAULT',
  SchedulableTriggerInputTypes: { DATE: 'date', TIME_INTERVAL: 'timeInterval' },
}));

// Mock api/client — getApiClient is a jest.fn() whose return value
// is configured in beforeEach (avoids the jest.mock hoisting issue with consts)
jest.mock('../../api/client', () => ({
  getApiClient: jest.fn(),
}));

// ── test helpers ──────────────────────────────────────────────────────────────

import { getApiClient } from '../../api/client';
import { registerNotificationHandlers } from '../handlers';

const mockPost = jest.fn().mockResolvedValue({ data: {}, error: null });

beforeEach(() => {
  jest.clearAllMocks();
  responseListener = null;
  // Set up getApiClient to return an object with a POST mock
  (getApiClient as jest.Mock).mockResolvedValue({ POST: mockPost });
  registerNotificationHandlers();
});

function makeResponse(actionId: string, dataOverride: Record<string, unknown> = {}) {
  const defaultData = {
    fire_key: 'rem-001:2026-05-21T08:00:00+05:30',
    tracked_item_id: 'item-001',
    category: 'medication',
  };
  return {
    actionIdentifier: actionId,
    notification: {
      request: {
        identifier: defaultData.fire_key,
        content: {
          title: 'Test',
          body: 'Test body',
          data: { ...defaultData, ...dataOverride },
        },
      },
    },
  };
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('registerNotificationHandlers', () => {
  it('registers a listener on mount', () => {
    expect(responseListener).toBeTruthy();
  });
});

describe('action: taken', () => {
  it('POSTs action=taken with fire_key', async () => {
    await responseListener!(makeResponse('taken'));

    expect(mockPost).toHaveBeenCalledTimes(1);
    const body = mockPost.mock.calls[0][1].body;
    expect(body.action).toBe('taken');
    expect(body.fire_key).toBe('rem-001:2026-05-21T08:00:00+05:30');
    expect(body.tracked_item_id).toBe('item-001');
    expect(body.occurred_at).toBeDefined();
  });
});

describe('action: skipped', () => {
  it('POSTs action=skipped', async () => {
    await responseListener!(makeResponse('skipped'));

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][1].body.action).toBe('skipped');
  });
});

describe('action: logged_value', () => {
  it('POSTs action=logged_value for water category', async () => {
    await responseListener!(makeResponse('logged_value', { category: 'water' }));

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][1].body.action).toBe('logged_value');
  });
});

describe('action: snooze_15', () => {
  it('schedules a 15-minute local notification without POSTing to API', async () => {
    await responseListener!(makeResponse('snooze_15'));

    expect(mockPost).not.toHaveBeenCalled();
    expect(mockSchedule).toHaveBeenCalledTimes(1);

    const req = mockSchedule.mock.calls[0][0];
    expect(req.trigger.type).toBe('timeInterval');
    expect(req.trigger.seconds).toBe(900); // 15 × 60
    expect(req.trigger.repeats).toBe(false);
  });

  it('uses a unique snooze identifier (not the original fire_key)', async () => {
    await responseListener!(makeResponse('snooze_15'));

    const req = mockSchedule.mock.calls[0][0];
    expect(req.identifier).toMatch(/^snooze-/);
    expect(req.identifier).not.toBe('rem-001:2026-05-21T08:00:00+05:30');
  });
});

describe('action: DEFAULT (bare tap)', () => {
  it('does not POST or schedule on bare notification tap', async () => {
    await responseListener!(
      makeResponse('expo.modules.notifications.actions.DEFAULT')
    );

    expect(mockPost).not.toHaveBeenCalled();
    expect(mockSchedule).not.toHaveBeenCalled();
  });
});

describe('missing data guard', () => {
  it('does nothing if fire_key is absent', async () => {
    await responseListener!(
      makeResponse('taken', { fire_key: undefined, tracked_item_id: undefined })
    );

    expect(mockPost).not.toHaveBeenCalled();
  });
});
