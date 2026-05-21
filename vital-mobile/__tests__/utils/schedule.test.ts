import { formatScheduleSummary, defaultTimesForDoses, estimateExpectedFires } from '../../src/utils/schedule';

describe('formatScheduleSummary', () => {
  it('formats recurring daily schedule', () => {
    const s = formatScheduleSummary({
      type: 'recurring',
      times: ['08:00', '20:00'],
      days_of_week: ['mon','tue','wed','thu','fri','sat','sun'],
    });
    expect(s).toContain('08:00');
    expect(s).toContain('20:00');
    expect(s.toLowerCase()).toContain('daily');
  });

  it('formats interval schedule', () => {
    const s = formatScheduleSummary({
      type: 'interval',
      interval_minutes: 120,
      active_window: { start: '08:00', end: '22:00' },
      days_of_week: ['mon','tue','wed','thu','fri'],
    });
    expect(s).toContain('2h');
    expect(s).toContain('08:00');
  });

  it('returns empty string for null', () => {
    expect(formatScheduleSummary(null)).toBe('');
  });
});

describe('defaultTimesForDoses', () => {
  it('returns 1 time for 1 dose', () => {
    expect(defaultTimesForDoses(1)).toHaveLength(1);
  });

  it('returns 2 times for 2 doses', () => {
    const times = defaultTimesForDoses(2);
    expect(times).toHaveLength(2);
    expect(times).toContain('08:00');
    expect(times).toContain('20:00');
  });

  it('returns correct count for all supported values', () => {
    [1, 2, 3, 4, 5, 6].forEach((n) => {
      expect(defaultTimesForDoses(n)).toHaveLength(n);
    });
  });
});

describe('estimateExpectedFires', () => {
  it('estimates recurring schedule fires', () => {
    const fires = estimateExpectedFires(
      { type: 'recurring', times: ['08:00', '20:00'], days_of_week: ['mon','tue','wed','thu','fri','sat','sun'] },
      30
    );
    expect(fires).toBe(60); // 2 times * 7/7 * 30 days
  });

  it('estimates interval schedule fires', () => {
    const fires = estimateExpectedFires(
      { type: 'interval', interval_minutes: 120, active_window: { start: '08:00', end: '22:00' }, days_of_week: ['mon','tue','wed','thu','fri','sat','sun'] },
      30
    );
    // 14h window / 2h interval = 7 fires/day * 30 days
    expect(fires).toBe(210);
  });

  it('returns 0 for null', () => {
    expect(estimateExpectedFires(null, 30)).toBe(0);
  });
});
