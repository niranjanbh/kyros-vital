/**
 * Today screen smoke test.
 * Mocks all API hooks so the screen renders without a real backend.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '../../src/theme/ThemeProvider';

// ── mock expo-router ──────────────────────────────────────────────────────────
jest.mock('expo-router', () => ({
  router: { push: jest.fn() },
  useLocalSearchParams: () => ({}),
}));

// ── mock expo-haptics ─────────────────────────────────────────────────────────
jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'Light' },
}));

// ── mock permission status (avoids expo-notifications native module call) ─────
jest.mock('../../src/hooks/usePermissionStatus', () => ({
  usePermissionStatus: () => 'granted',
}));

// ── mock the query hooks ──────────────────────────────────────────────────────
const mockUseUpcoming = jest.fn(() => ({ data: [], isLoading: false }));
const mockUseItems = jest.fn(() => ({ data: [] }));
const mockUseMeasurements = jest.fn(() => ({ data: [] }));
const mockUseWeekLogs = jest.fn(() => ({ data: [] }));

jest.mock('../../src/api/queries', () => ({
  useUpcomingReminders: (...args: any[]) => mockUseUpcoming(...args),
  useTrackedItems: (...args: any[]) => mockUseItems(...args),
  useRecentMeasurements: (...args: any[]) => mockUseMeasurements(...args),
  useWeekLogs: (...args: any[]) => mockUseWeekLogs(...args),
  useLogEntry: () => ({ mutate: jest.fn() }),
}));

// ── mock date-fns to return stable values ─────────────────────────────────────
jest.mock('date-fns', () => ({
  ...jest.requireActual('date-fns'),
  format: (date: Date, fmt: string) => {
    if (fmt === 'EEEE, d MMMM') return 'Wednesday, 21 May';
    if (fmt === 'HH:mm') return '08:00';
    return fmt;
  },
}));

// ── helpers ───────────────────────────────────────────────────────────────────
function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}

// Static import — mocks declared above are hoisted before this runs
import TodayScreen from '../../app/(tabs)/index';

// ── tests ─────────────────────────────────────────────────────────────────────

describe('TodayScreen', () => {
  it('renders without crashing', () => {
    const { toJSON } = render(<TodayScreen />, { wrapper });
    expect(toJSON()).toBeTruthy();
  });

  it('shows greeting text', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    // Should show one of the greetings
    const greetings = ['Good morning', 'Good afternoon', 'Good evening'];
    const found = greetings.some((g) => {
      try { getByText(g); return true; } catch { return false; }
    });
    expect(found).toBe(true);
  });

  it('shows TODAY section label', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    expect(getByText('TODAY')).toBeTruthy();
  });

  it('shows empty state when no fires', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    expect(getByText('Nothing scheduled for today')).toBeTruthy();
  });

  it('hides measurements section when no data', () => {
    const { queryByText } = render(<TodayScreen />, { wrapper });
    expect(queryByText('RECENT')).toBeNull();
  });

  it('hides this week section when no data', () => {
    const { queryByText } = render(<TodayScreen />, { wrapper });
    expect(queryByText('THIS WEEK')).toBeNull();
  });
});

describe('TodayScreen with data', () => {
  beforeEach(() => {
    mockUseItems.mockReturnValue({
      data: [
        {
          id: 'item-001',
          category: 'medication',
          name: 'Metformin 500mg',
          metadata: { drug_name: 'Metformin', dosage: '500mg', with_food: true },
        },
      ],
    });

    mockUseUpcoming.mockReturnValue({
      data: [
        {
          reminder_id: 'rem-001',
          tracked_item_id: 'item-001',
          fire_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
          fire_key: 'rem-001:upcoming',
          payload: {
            title: 'Medication',
            body: 'Take Metformin 500mg',
            category: 'medication',
            actions: ['taken', 'skipped', 'snooze_15'],
          },
        },
      ],
      isLoading: false,
    });

    mockUseMeasurements.mockReturnValue({
      data: [
        { id: 'm1', type: 'weight', value: '72.4', unit: 'kg', measured_at: new Date().toISOString() },
        { id: 'm2', type: 'weight', value: '72.1', unit: 'kg', measured_at: new Date(Date.now() - 86400000).toISOString() },
      ],
    });

    mockUseWeekLogs.mockReturnValue({
      data: [
        { id: 'l1', action: 'taken', tracked_item_id: 'item-001', occurred_at: new Date().toISOString() },
      ],
    });
  });

  afterEach(() => {
    mockUseUpcoming.mockReset();
    mockUseItems.mockReset();
    mockUseMeasurements.mockReset();
    mockUseWeekLogs.mockReset();
  });

  it('renders timeline item', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    expect(getByText('Take Metformin 500mg')).toBeTruthy();
  });

  it('shows RECENT section when measurements exist', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    expect(getByText('RECENT')).toBeTruthy();
  });

  it('shows THIS WEEK section when logs and items exist', () => {
    const { getByText } = render(<TodayScreen />, { wrapper });
    expect(getByText('THIS WEEK')).toBeTruthy();
  });
});
