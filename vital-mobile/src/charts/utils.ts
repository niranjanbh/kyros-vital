/** Chart utilities for the measurements feature. */

// ── type metadata ─────────────────────────────────────────────────────────────

export const MEASUREMENT_META: Record<
  string,
  { label: string; unit: string; defaultUnit: string }
> = {
  weight:          { label: 'Weight',          unit: 'kg',    defaultUnit: 'kg' },
  bp_systolic:     { label: 'Systolic BP',      unit: 'mmHg',  defaultUnit: 'mmHg' },
  bp_diastolic:    { label: 'Diastolic BP',     unit: 'mmHg',  defaultUnit: 'mmHg' },
  heart_rate:      { label: 'Heart Rate',       unit: 'bpm',   defaultUnit: 'bpm' },
  fasting_glucose: { label: 'Fasting Glucose',  unit: 'mg/dL', defaultUnit: 'mg/dL' },
  hba1c:           { label: 'HbA1c',            unit: '%',     defaultUnit: '%' },
  body_temp:       { label: 'Body Temp',        unit: '°C',    defaultUnit: '°C' },
  steps:           { label: 'Steps',            unit: 'steps', defaultUnit: 'steps' },
};

export const ALL_MEASUREMENT_TYPES = Object.keys(MEASUREMENT_META);

// ── formatValue ───────────────────────────────────────────────────────────────

/**
 * Returns a human-readable formatted string with unit.
 * Examples: formatValue('weight', 72.4) → '72.4 kg'
 *           formatValue('hba1c', 5.6) → '5.6%'
 */
export function formatValue(type: string, value: number | string): string {
  const meta = MEASUREMENT_META[type];
  const unit = meta?.unit ?? '';
  const n = parseFloat(String(value));
  if (isNaN(n)) return `— ${unit}`.trim();

  const precision =
    type === 'hba1c' || type === 'body_temp' ? 1 : type === 'steps' ? 0 : 1;

  const formatted = type === 'steps' ? Math.round(n).toLocaleString() : n.toFixed(precision);

  // Units that attach without a space: %, °C
  const noSpace = unit === '%' || unit === '°C';
  return noSpace ? `${formatted}${unit}` : `${formatted} ${unit}`.trim();
}

// ── trendDirection ────────────────────────────────────────────────────────────

export type TrendResult = {
  direction: 'up' | 'down' | 'flat';
  /** Absolute delta as a percentage of the average */
  deltaPct: number;
  /** Raw numeric delta (latest - average) */
  delta: number;
};

/**
 * Compares the latest value against the mean of all values.
 * Returns 'flat' if the delta is within 1% of the average.
 */
export function trendDirection(values: number[]): TrendResult {
  if (values.length < 2) {
    return { direction: 'flat', deltaPct: 0, delta: 0 };
  }

  const latest = values[values.length - 1];
  const avg = values.reduce((s, v) => s + v, 0) / values.length;
  const delta = latest - avg;
  const deltaPct = avg !== 0 ? Math.abs(delta / avg) * 100 : 0;

  const direction =
    deltaPct < 1 ? 'flat' : delta > 0 ? 'up' : 'down';

  return { direction, delta, deltaPct };
}

export const TREND_INDICATOR: Record<TrendResult['direction'], string> = {
  up:   '▲',
  down: '▼',
  flat: '—',
};

// ── mergeBPRows ───────────────────────────────────────────────────────────────

export type BPPair = {
  measured_at: string;
  systolic: number;
  diastolic: number;
};

/**
 * Pairs bp_systolic and bp_diastolic measurements by measured_at timestamp.
 * Rows without a counterpart are dropped.
 */
export function mergeBPRows(measurements: any[]): BPPair[] {
  const systolic = measurements.filter((m) => m.type === 'bp_systolic');
  const diastolic = measurements.filter((m) => m.type === 'bp_diastolic');

  const diastolicByTime: Record<string, number> = {};
  for (const d of diastolic) {
    // Key by minute-precision so a few ms of clock skew don't matter
    const key = d.measured_at.slice(0, 16);
    diastolicByTime[key] = parseFloat(String(d.value));
  }

  const pairs: BPPair[] = [];
  for (const s of systolic) {
    const key = s.measured_at.slice(0, 16);
    if (diastolicByTime[key] !== undefined) {
      pairs.push({
        measured_at: s.measured_at,
        systolic: parseFloat(String(s.value)),
        diastolic: diastolicByTime[key],
      });
    }
  }

  return pairs.sort(
    (a, b) => new Date(a.measured_at).getTime() - new Date(b.measured_at).getTime()
  );
}

// ── date range helpers ────────────────────────────────────────────────────────

export function rangeStartDate(range: '7d' | '30d' | '90d' | '1y' | 'all'): Date | null {
  if (range === 'all') return null;
  const now = new Date();
  const days = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 }[range];
  return new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
}
