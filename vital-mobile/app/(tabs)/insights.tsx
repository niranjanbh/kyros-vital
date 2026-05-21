import React, { useMemo } from 'react';
import {
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { EmptyState } from '../../src/components/EmptyState';
import {
  useTrackedItems,
  useMonthLogs,
  useRecentMeasurements,
  useLabReports,
} from '../../src/api/queries';
import { trendDirection, TREND_INDICATOR, formatValue, MEASUREMENT_META } from '../../src/charts/utils';

// ── adherence computation ─────────────────────────────────────────────────────

const ADHERENCE_CATEGORIES = ['medication', 'water', 'workout'] as const;
type AdherenceCategory = typeof ADHERENCE_CATEGORIES[number];

const ADHERENCE_LABELS: Record<AdherenceCategory, string> = {
  medication: 'Medications',
  water: 'Hydration',
  workout: 'Workouts',
};

interface AdherenceRow {
  category: AdherenceCategory;
  label: string;
  days: number;
  rate: number;
}

function computeAdherence(items: any[], logs: any[]): AdherenceRow[] {
  const rows: AdherenceRow[] = [];

  for (const cat of ADHERENCE_CATEGORIES) {
    const catItems = items.filter((i) => i.status !== 'discontinued' && i.category === cat);
    if (catItems.length === 0) continue;

    let days = 0;

    if (cat === 'medication') {
      days = new Set(
        logs
          .filter((l) => l.action === 'taken')
          .map((l) => (l.occurred_at as string).slice(0, 10))
      ).size;
    } else if (cat === 'water') {
      const waterIds = new Set(catItems.map((i: any) => i.id));
      days = new Set(
        logs
          .filter((l) => l.action === 'logged_value' && waterIds.has(l.tracked_item_id))
          .map((l) => (l.occurred_at as string).slice(0, 10))
      ).size;
    } else if (cat === 'workout') {
      const workoutIds = new Set(catItems.map((i: any) => i.id));
      days = new Set(
        logs
          .filter((l) => l.action === 'taken' && workoutIds.has(l.tracked_item_id))
          .map((l) => (l.occurred_at as string).slice(0, 10))
      ).size;
    }

    rows.push({
      category: cat,
      label: ADHERENCE_LABELS[cat],
      days,
      rate: Math.min(1, days / 30),
    });
  }

  return rows;
}

// ── measurement trend computation ─────────────────────────────────────────────

interface TrendRow {
  type: string;
  label: string;
  current: string;
  direction: '▲' | '▼' | '—';
}

function computeTrendRows(measurements: any[]): TrendRow[] {
  const byType: Record<string, any[]> = {};
  for (const m of measurements) {
    if (!byType[m.type]) byType[m.type] = [];
    byType[m.type].push(m);
  }

  return Object.entries(byType).map(([type, rows]) => {
    const sorted = [...rows].sort(
      (a, b) => new Date(a.measured_at).getTime() - new Date(b.measured_at).getTime()
    );
    const values = sorted.map((m) => parseFloat(String(m.value)));
    const { direction } = trendDirection(values);
    const latest = values[values.length - 1];
    return {
      type,
      label: MEASUREMENT_META[type]?.label ?? type,
      current: formatValue(type, latest),
      direction: TREND_INDICATOR[direction] as '▲' | '▼' | '—',
    };
  });
}

// ── section header ────────────────────────────────────────────────────────────

function SectionHeader({ label }: { label: string }) {
  return (
    <Text variant="label" color="mist" style={styles.sectionLabel}>
      {label}
    </Text>
  );
}

// ── adherence bar ─────────────────────────────────────────────────────────────

function AdherenceBar({ rate }: { rate: number }) {
  const filled = Math.max(0.001, rate);
  const empty = Math.max(0.001, 1 - rate);
  return (
    <View style={styles.barTrack}>
      <View style={[styles.barFilled, { flex: filled }]} />
      <View style={[styles.barEmpty, { flex: empty }]} />
    </View>
  );
}

// ── main screen ───────────────────────────────────────────────────────────────

export default function InsightsScreen() {
  const qc = useQueryClient();
  const [refreshing, setRefreshing] = React.useState(false);

  const { data: rawItems = [] } = useTrackedItems();
  const { data: rawMonthLogs = [] } = useMonthLogs();
  const { data: rawMeasurements = [] } = useRecentMeasurements();
  const { data: rawLabReports = [] } = useLabReports();

  const items = rawItems as any[];
  const monthLogs = rawMonthLogs as any[];
  const measurements = rawMeasurements as any[];
  const labReports = rawLabReports as any[];

  const adherenceRows = useMemo(
    () => computeAdherence(items, monthLogs),
    [items, monthLogs]
  );

  const trendRows = useMemo(
    () => computeTrendRows(measurements),
    [measurements]
  );

  // Lab summary: last 90 days
  const { labCount, flaggedCount } = useMemo(() => {
    const cutoff = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);
    const recent = labReports.filter(
      (r: any) => new Date(r.report_date) >= cutoff
    );
    const flagged = recent.reduce((acc: number, r: any) => {
      const parsed = (r.parsed ?? []) as any[];
      return acc + parsed.filter((t: any) => t.flag !== 'normal').length;
    }, 0);
    return { labCount: recent.length, flaggedCount: flagged };
  }, [labReports]);

  const isEmpty = monthLogs.length === 0 && measurements.length === 0;

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['tracked-items'] }),
      qc.invalidateQueries({ queryKey: ['logs-month'] }),
      qc.invalidateQueries({ queryKey: ['measurements-recent-30d'] }),
      qc.invalidateQueries({ queryKey: ['lab-reports'] }),
    ]);
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={tokens.mist}
          />
        }
      >
        <Text variant="displayM" color="ink" style={styles.heading}>
          Insights
        </Text>

        {isEmpty ? (
          <EmptyState
            title="Keep going"
            body="Insights appear after your first week of tracking."
          />
        ) : (
          <>
            {/* Adherence card */}
            {adherenceRows.length > 0 && (
              <View style={styles.section}>
                <SectionHeader label="ADHERENCE · LAST 30 DAYS" />
                <View style={styles.card}>
                  {adherenceRows.map((row, idx) => (
                    <React.Fragment key={row.category}>
                      {idx > 0 && <View style={styles.divider} />}
                      <View style={styles.adherenceRow}>
                        <View style={styles.adherenceLabelRow}>
                          <Text variant="body" color="ink">{row.label}</Text>
                          <Text variant="caption" color="mist">
                            {row.days}/30 days
                          </Text>
                        </View>
                        <AdherenceBar rate={row.rate} />
                      </View>
                    </React.Fragment>
                  ))}
                </View>
              </View>
            )}

            {/* Trends card */}
            {trendRows.length > 0 && (
              <View style={styles.section}>
                <SectionHeader label="TRENDS · LAST 30 DAYS" />
                <View style={styles.card}>
                  {trendRows.map((row, idx) => (
                    <React.Fragment key={row.type}>
                      {idx > 0 && <View style={styles.divider} />}
                      <Pressable
                        style={({ pressed }) => [
                          styles.trendRow,
                          pressed && { opacity: 0.7 },
                        ]}
                        onPress={() => router.push(`/measurement/${row.type}` as any)}
                        accessibilityLabel={`${row.label}: ${row.current}, trend ${row.direction}`}
                        accessibilityRole="button"
                      >
                        <Text variant="body" color="ink" style={{ flex: 1 }}>
                          {row.label}
                        </Text>
                        <Text variant="mono" color="slate" style={styles.trendValue}>
                          {row.current}
                        </Text>
                        <Text variant="mono" color="mist" style={styles.trendArrow}>
                          {row.direction}
                        </Text>
                      </Pressable>
                    </React.Fragment>
                  ))}
                </View>
              </View>
            )}

            {/* Lab summary card */}
            <View style={styles.section}>
              <SectionHeader label="LAB REPORTS · LAST 90 DAYS" />
              <View style={styles.card}>
                <View style={styles.labRow}>
                  <Text variant="body" color="ink">
                    {labCount} report{labCount !== 1 ? 's' : ''}
                    {' · '}
                    {flaggedCount} flagged test{flaggedCount !== 1 ? 's' : ''}
                  </Text>
                </View>
              </View>
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  content: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s24,
    paddingBottom: tokens.s48,
    gap: tokens.s32,
  },
  heading: {},
  section: { gap: tokens.s12 },
  sectionLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  card: {
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    overflow: 'hidden',
  },
  divider: { height: 1, backgroundColor: tokens.hairline },

  // Adherence
  adherenceRow: {
    paddingVertical: tokens.s12,
    paddingHorizontal: tokens.s16,
    gap: tokens.s8,
  },
  adherenceLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  barTrack: {
    flexDirection: 'row',
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
  },
  barFilled: {
    backgroundColor: tokens.ink,
    height: 4,
  },
  barEmpty: {
    backgroundColor: tokens.hairline,
    height: 4,
  },

  // Trends
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: tokens.s12,
    paddingHorizontal: tokens.s16,
    gap: tokens.s8,
  },
  trendValue: {
    fontSize: 13,
  },
  trendArrow: {
    fontSize: 13,
    width: 16,
    textAlign: 'right',
  },

  // Lab
  labRow: {
    paddingVertical: tokens.s12,
    paddingHorizontal: tokens.s16,
  },
});
