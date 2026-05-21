import {
  formatValue,
  trendDirection,
  mergeBPRows,
  rangeStartDate,
  MEASUREMENT_META,
} from '../utils';

// ── formatValue ───────────────────────────────────────────────────────────────

describe('formatValue', () => {
  it('formats weight with one decimal and kg unit', () => {
    expect(formatValue('weight', 72.4)).toBe('72.4 kg');
  });

  it('formats hba1c with % attached (no space)', () => {
    expect(formatValue('hba1c', 5.6)).toBe('5.6%');
  });

  it('formats body temp with °C attached (no space)', () => {
    expect(formatValue('body_temp', 37.0)).toBe('37.0°C');
  });

  it('formats steps as rounded integer with comma for thousands', () => {
    expect(formatValue('steps', 10500)).toBe('10,500 steps');
  });

  it('formats heart rate', () => {
    expect(formatValue('heart_rate', 72)).toBe('72.0 bpm');
  });

  it('formats fasting glucose', () => {
    expect(formatValue('fasting_glucose', 95.5)).toBe('95.5 mg/dL');
  });

  it('returns em dash for NaN value', () => {
    expect(formatValue('weight', NaN)).toContain('—');
  });

  it('handles string values', () => {
    expect(formatValue('weight', '72.4')).toBe('72.4 kg');
  });
});

// ── trendDirection ────────────────────────────────────────────────────────────

describe('trendDirection', () => {
  it('returns flat for single value', () => {
    const result = trendDirection([72.4]);
    expect(result.direction).toBe('flat');
    expect(result.delta).toBe(0);
  });

  it('returns flat when delta < 1% of average', () => {
    // Average 100, latest 100.5 → delta = 0.5 → deltaPct = 0.5%
    const result = trendDirection([99.5, 100, 100, 100, 100.5]);
    expect(result.direction).toBe('flat');
  });

  it('returns up when latest > average by ≥1%', () => {
    // Average = 70, latest = 75
    const result = trendDirection([70, 70, 70, 75]);
    expect(result.direction).toBe('up');
    expect(result.delta).toBeGreaterThan(0);
  });

  it('returns down when latest < average by ≥1%', () => {
    const result = trendDirection([75, 75, 75, 70]);
    expect(result.direction).toBe('down');
    expect(result.delta).toBeLessThan(0);
  });

  it('returns flat for empty array', () => {
    expect(trendDirection([]).direction).toBe('flat');
  });

  it('includes deltaPct > 0 when trend is up', () => {
    const result = trendDirection([100, 100, 110]);
    expect(result.deltaPct).toBeGreaterThan(0);
    expect(result.direction).toBe('up');
  });
});

// ── mergeBPRows ───────────────────────────────────────────────────────────────

describe('mergeBPRows', () => {
  const baseTime = '2026-05-20T08:00:00Z';
  const baseTime2 = '2026-05-20T09:00:00Z';

  it('pairs systolic and diastolic by measured_at minute', () => {
    const measurements = [
      { type: 'bp_systolic',  value: '120', measured_at: baseTime },
      { type: 'bp_diastolic', value: '80',  measured_at: baseTime },
    ];
    const pairs = mergeBPRows(measurements);
    expect(pairs).toHaveLength(1);
    expect(pairs[0].systolic).toBe(120);
    expect(pairs[0].diastolic).toBe(80);
    expect(pairs[0].measured_at).toBe(baseTime);
  });

  it('drops unpaired readings', () => {
    const measurements = [
      { type: 'bp_systolic',  value: '120', measured_at: baseTime },
      { type: 'bp_diastolic', value: '80',  measured_at: baseTime2 }, // different time
    ];
    const pairs = mergeBPRows(measurements);
    expect(pairs).toHaveLength(0);
  });

  it('handles multiple paired readings sorted oldest first', () => {
    const measurements = [
      { type: 'bp_systolic',  value: '118', measured_at: baseTime2 },
      { type: 'bp_diastolic', value: '76',  measured_at: baseTime2 },
      { type: 'bp_systolic',  value: '120', measured_at: baseTime },
      { type: 'bp_diastolic', value: '80',  measured_at: baseTime },
    ];
    const pairs = mergeBPRows(measurements);
    expect(pairs).toHaveLength(2);
    expect(pairs[0].measured_at).toBe(baseTime); // oldest first
    expect(pairs[1].measured_at).toBe(baseTime2);
  });

  it('returns empty array for empty input', () => {
    expect(mergeBPRows([])).toEqual([]);
  });
});

// ── rangeStartDate ────────────────────────────────────────────────────────────

describe('rangeStartDate', () => {
  it('returns null for "all"', () => {
    expect(rangeStartDate('all')).toBeNull();
  });

  it('returns a date approximately 7 days ago for "7d"', () => {
    const now = Date.now();
    const result = rangeStartDate('7d');
    expect(result).toBeTruthy();
    const diffDays = (now - result!.getTime()) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBeCloseTo(7, 0);
  });

  it('returns a date approximately 30 days ago for "30d"', () => {
    const result = rangeStartDate('30d');
    const diffDays = (Date.now() - result!.getTime()) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBeCloseTo(30, 0);
  });
});

// ── MEASUREMENT_META ──────────────────────────────────────────────────────────

describe('MEASUREMENT_META', () => {
  it('has entries for all supported types', () => {
    const required = [
      'weight', 'bp_systolic', 'bp_diastolic', 'heart_rate',
      'fasting_glucose', 'hba1c', 'body_temp', 'steps',
    ];
    required.forEach((t) => expect(MEASUREMENT_META).toHaveProperty(t));
  });

  it('weight has kg as default unit', () => {
    expect(MEASUREMENT_META.weight.defaultUnit).toBe('kg');
  });
});
