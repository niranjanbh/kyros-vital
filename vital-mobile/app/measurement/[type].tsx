import React, { useMemo, useState } from 'react';
import {
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, Plus, Trash2 } from 'lucide-react-native';
import { CartesianChart, Line } from 'victory-native';
import { format, parseISO } from 'date-fns';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Card } from '../../src/components/Card';
import {
  MEASUREMENT_META,
  formatValue,
  trendDirection,
  TREND_INDICATOR,
  mergeBPRows,
  rangeStartDate,
} from '../../src/charts/utils';
import { useMeasurements } from '../../src/api/queries';
import { getApiClient } from '../../src/api/client';

type Range = '7d' | '30d' | '90d' | '1y' | 'all';
const RANGES: Range[] = ['7d', '30d', '90d', '1y', 'all'];

export default function MeasurementTypeScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const [range, setRange] = useState<Range>('30d');
  const qc = useQueryClient();

  const isBP = type === 'bp';
  const meta = isBP
    ? { label: 'Blood Pressure', unit: 'mmHg' }
    : MEASUREMENT_META[type ?? 'weight'];

  const rangeStart = rangeStartDate(range);
  const from = rangeStart?.toISOString();

  const { data: rawData = [] } = useMeasurements(isBP ? undefined : type, from);
  const { data: rawSystolic = [] } = useMeasurements(isBP ? 'bp_systolic' : undefined, from);
  const { data: rawDiastolic = [] } = useMeasurements(isBP ? 'bp_diastolic' : undefined, from);

  const deleteMeasurement = useMutation({
    mutationFn: async (id: string) => {
      const client = await getApiClient();
      const { error } = await client.DELETE(
        '/v1/wellness/measurements/{measurement_id}',
        { params: { path: { measurement_id: id } } }
      );
      if (error) throw error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['measurements'] });
      qc.invalidateQueries({ queryKey: ['measurements-recent-30d'] });
    },
  });

  const { chartData, latestValue, trendResult, referenceRange } = useMemo(() => {
    if (isBP) {
      const pairs = mergeBPRows([...(rawSystolic as any[]), ...(rawDiastolic as any[])]);
      const lastPair = pairs[pairs.length - 1];
      const chartRows = pairs.map((p, i) => ({
        x: i,
        systolic: p.systolic,
        diastolic: p.diastolic,
      }));
      return {
        chartData: chartRows,
        latestValue: lastPair ? `${lastPair.systolic}/${lastPair.diastolic}` : '—',
        trendResult: trendDirection(pairs.map((p) => p.systolic)),
        referenceRange: null,
      };
    }

    const measurements = (rawData as any[]).filter((m) => m.type === type);
    const sorted = [...measurements].sort(
      (a, b) => new Date(a.measured_at).getTime() - new Date(b.measured_at).getTime()
    );
    const values = sorted.map((m) => parseFloat(String(m.value)));
    const chartRows = sorted.map((m, i) => ({
      x: i,
      y: parseFloat(String(m.value)),
    }));
    const latest = values[values.length - 1];
    const refRange = sorted[sorted.length - 1]?.reference_range as
      | { low?: number; high?: number }
      | null;

    return {
      chartData: chartRows,
      latestValue: latest !== undefined ? formatValue(type ?? '', latest) : '—',
      trendResult: trendDirection(values),
      referenceRange: refRange ?? null,
    };
  }, [isBP, rawData, rawSystolic, rawDiastolic, type]);

  const handleDelete = (id: string) => {
    Alert.alert('Delete measurement?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => deleteMeasurement.mutate(id),
      },
    ]);
  };

  const trendColor = trendResult.direction === 'flat' ? tokens.mist : tokens.positive;

  const listItems = isBP
    ? mergeBPRows([...(rawSystolic as any[]), ...(rawDiastolic as any[])]).reverse()
    : (rawData as any[])
        .filter((m) => m.type === type)
        .sort(
          (a, b) => new Date(b.measured_at).getTime() - new Date(a.measured_at).getTime()
        );

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
        <Pressable onPress={() => router.push('/measurement/new')} hitSlop={12}>
          <Plus size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* Title + latest value */}
        <View style={styles.titleBlock}>
          <Text variant="displayM" color="ink">{meta?.label}</Text>
          <View style={styles.valueRow}>
            {isBP ? (
              <Text variant="displayXL" color="ink" style={styles.bigValue}>
                {latestValue}
              </Text>
            ) : (
              <>
                <Text variant="displayXL" color="ink" style={styles.bigValue}>
                  {String(latestValue).split(' ')[0]}
                </Text>
                <Text variant="body" color="slate" style={styles.unitLabel}>
                  {meta?.unit}
                </Text>
              </>
            )}
          </View>
          {trendResult.deltaPct >= 1 && (
            <View style={styles.trendRow}>
              <Text variant="mono" style={{ color: trendColor, fontSize: 14 }}>
                {TREND_INDICATOR[trendResult.direction]}
              </Text>
              <Text variant="bodySmall" style={{ color: trendColor, marginLeft: tokens.s4 }}>
                {trendResult.deltaPct.toFixed(1)}%
              </Text>
              <Text variant="bodySmall" color="mist" style={{ marginLeft: tokens.s4 }}>
                vs avg
              </Text>
            </View>
          )}
        </View>

        {/* Range chips */}
        <View style={styles.rangeRow}>
          {RANGES.map((r) => (
            <Pressable
              key={r}
              style={({ pressed }) => [
                styles.rangeChip,
                r === range && styles.rangeChipActive,
                pressed && { opacity: 0.7 },
              ]}
              onPress={() => setRange(r)}
            >
              <Text
                variant="bodySmall"
                color={r === range ? 'ink' : 'slate'}
                style={r === range ? { fontFamily: 'GeistSans-Medium' } : undefined}
              >
                {r === 'all' ? 'All' : r}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Victory Native XL chart */}
        {chartData.length >= 2 ? (
          <Card style={styles.chartCard}>
            <View style={styles.chartWrapper}>
              <CartesianChart
                data={chartData}
                xKey="x"
                yKeys={isBP ? (['systolic', 'diastolic'] as any) : (['y'] as any)}
                axisOptions={{
                  font: null,
                  lineColor: tokens.hairline,
                  labelColor: tokens.mist,
                  axisSide: { x: 'bottom', y: 'left' },
                  tickCount: { x: 0, y: 4 },
                  formatYLabel: (v: any) => String(Number(v).toFixed(0)),
                }}
                domainPadding={{ top: 24, bottom: 8 }}
              >
                {({ points }: any) => (
                  <>
                    {/* Reference range band — hairline horizontal stripe */}
                    {referenceRange && !isBP && (
                      <ReferenceBand
                        points={(points as any).y}
                        low={referenceRange.low}
                        high={referenceRange.high}
                      />
                    )}
                    <Line
                      points={isBP ? (points as any).systolic : (points as any).y}
                      color={tokens.chartLine}
                      strokeWidth={1.5}
                      curveType="natural"
                    />
                    {isBP && (
                      <Line
                        points={(points as any).diastolic}
                        color={tokens.slate}
                        strokeWidth={1.5}
                        curveType="natural"
                      />
                    )}
                  </>
                )}
              </CartesianChart>
            </View>
            {isBP && (
              <View style={styles.bpLegend}>
                <View style={[styles.legendDot, { backgroundColor: tokens.ink }]} />
                <Text variant="caption" color="mist">Systolic</Text>
                <View style={[styles.legendDot, { backgroundColor: tokens.slate, marginLeft: tokens.s12 }]} />
                <Text variant="caption" color="mist">Diastolic</Text>
              </View>
            )}
          </Card>
        ) : (
          <Card style={styles.chartCard}>
            <View style={styles.emptyChart}>
              <Text variant="bodySmall" color="mist">
                Add at least 2 readings to see the chart.
              </Text>
            </View>
          </Card>
        )}

        {/* Readings list */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            READINGS
          </Text>
          {listItems.length === 0 ? (
            <Text variant="bodySmall" color="mist">No readings in this range.</Text>
          ) : (
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {listItems.map((item: any, idx: number) => (
                <React.Fragment key={item.id ?? `bp-${idx}`}>
                  {idx > 0 && <View style={styles.divider} />}
                  <ReadingRow
                    item={item}
                    isBP={isBP}
                    type={type ?? 'weight'}
                    onDelete={() => !isBP && handleDelete(item.id)}
                  />
                </React.Fragment>
              ))}
            </Card>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Reference range band ──────────────────────────────────────────────────────

function ReferenceBand({ points, low, high }: { points: any[]; low?: number; high?: number }) {
  // victory-native render-prop passes Skia PointsArray; use path drawing
  // This requires Skia components — import inline to avoid top-level Skia
  // dependency in test environments
  if (!low && !high) return null;
  if (!points?.length) return null;

  const { Rect } = require('@shopify/react-native-skia');
  const firstPt = points.find((p: any) => p?.y != null);
  const lastPt = [...points].reverse().find((p: any) => p?.y != null);
  if (!firstPt || !lastPt) return null;

  // Approximate y-coordinates from point array
  const ys = points.filter((p: any) => p?.y != null).map((p: any) => p.y as number);
  const lowY = low != null ? Math.max(...ys.filter((y) => y >= (low ?? 0))) : Math.max(...ys);
  const highY = high != null ? Math.min(...ys.filter((y) => y <= (high ?? Infinity))) : Math.min(...ys);

  if (lowY <= highY) return null;

  return (
    <Rect
      x={firstPt.x}
      y={highY}
      width={lastPt.x - firstPt.x}
      height={lowY - highY}
      color={`${tokens.hairline}66`}
    />
  );
}

// ── Reading row ───────────────────────────────────────────────────────────────

function ReadingRow({
  item,
  isBP,
  type,
  onDelete,
}: {
  item: any;
  isBP: boolean;
  type: string;
  onDelete: () => void;
}) {
  const displayValue = isBP
    ? `${item.systolic}/${item.diastolic} mmHg`
    : formatValue(type, item.value);
  const dateStr = format(
    parseISO(item.measured_at ?? item.measured_at),
    'd MMM yyyy, HH:mm'
  );

  return (
    <View style={styles.readingRow}>
      <View style={{ flex: 1 }}>
        <Text variant="body" color="ink" style={{ fontFamily: 'GeistMono-Regular' }}>
          {displayValue}
        </Text>
        <Text variant="caption" color="mist">{dateStr}</Text>
        {item.note ? <Text variant="caption" color="slate">{item.note}</Text> : null}
      </View>
      {!isBP && (
        <Pressable
          onPress={onDelete}
          hitSlop={8}
          style={({ pressed }) => ({ opacity: pressed ? 0.5 : 1 })}
        >
          <Trash2 size={16} color={tokens.critical} strokeWidth={1.5} />
        </Pressable>
      )}
    </View>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s8,
  },
  content: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s8,
    paddingBottom: tokens.s48,
    gap: tokens.s24,
  },
  titleBlock: { gap: tokens.s8 },
  valueRow: { flexDirection: 'row', alignItems: 'flex-end', gap: tokens.s8 },
  bigValue: { fontSize: 56, lineHeight: 60 },
  unitLabel: { marginBottom: 8 },
  trendRow: { flexDirection: 'row', alignItems: 'center' },
  rangeRow: { flexDirection: 'row', gap: tokens.s8, flexWrap: 'wrap' },
  rangeChip: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: 5,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  rangeChipActive: { borderColor: tokens.ink, backgroundColor: tokens.divider },
  chartCard: { padding: 0, overflow: 'hidden' },
  chartWrapper: { height: 200 },
  emptyChart: {
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.s16,
  },
  bpLegend: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.s12,
    paddingTop: 0,
    gap: tokens.s4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  section: { gap: tokens.s12 },
  sectionLabel: { textTransform: 'uppercase', letterSpacing: 1 },
  divider: { height: 1, backgroundColor: tokens.hairline },
  readingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.s16,
    gap: tokens.s12,
  },
});
