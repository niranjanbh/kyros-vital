import React, { useState, useMemo } from 'react';
import {
  Linking,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { Settings, Pill, Droplet, Dumbbell, Utensils, Activity, Tag, Check, BellOff } from 'lucide-react-native';
import { format, parseISO } from 'date-fns';
import * as Haptics from 'expo-haptics';
import { usePermissionStatus } from '../../src/hooks/usePermissionStatus';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Card } from '../../src/components/Card';
import { Sparkline } from '../../src/components/Sparkline';
import { ActionSheet, SheetAction } from '../../src/components/ActionSheet';
import { useQueryClient } from '@tanstack/react-query';
import {
  useUpcomingReminders,
  useLogEntry,
  useTrackedItems,
  useRecentMeasurements,
  useWeekLogs,
} from '../../src/api/queries';
import { MEASUREMENT_META } from '../../src/charts/utils';

// ── constants ──────────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  medication:  tokens.categoryColors.medication,
  water:       tokens.categoryColors.water,
  workout:     tokens.categoryColors.workout,
  meal:        tokens.categoryColors.meal,
  vital_check: tokens.categoryColors.vital_check,
  custom:      tokens.categoryColors.custom,
};

// Measurement display helpers sourced from MEASUREMENT_META
function getMeasurementUnit(type: string): string {
  return MEASUREMENT_META[type]?.unit ?? '';
}
function getMeasurementLabel(type: string): string {
  return MEASUREMENT_META[type]?.label ?? type;
}

const ACTION_LABELS: Record<string, string> = {
  taken:        'Taken',
  skipped:      'Skipped',
  snooze_15:    'Snooze 15 min',
  logged_value: 'Logged',
  acknowledged: 'Acknowledge',
};

const ACTION_API: Record<string, string> = {
  taken:        'taken',
  skipped:      'skipped',
  snooze_15:    'snoozed',
  logged_value: 'logged_value',
  acknowledged: 'acknowledged',
};

// ── helpers ────────────────────────────────────────────────────────────────────

function useGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function CategoryIcon({ category, size = 16 }: { category: string; size?: number }) {
  const color = CATEGORY_COLORS[category] ?? tokens.mist;
  const props = { size, color, strokeWidth: 1.5 };
  switch (category) {
    case 'medication':  return <Pill {...props} />;
    case 'water':       return <Droplet {...props} />;
    case 'workout':     return <Dumbbell {...props} />;
    case 'meal':        return <Utensils {...props} />;
    case 'vital_check': return <Activity {...props} />;
    default:            return <Tag {...props} />;
  }
}

function resolveTemplate(template: string, meta: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    const val = meta[key];
    return val != null ? String(val) : `{${key}}`;
  });
}

function getFireSubtitle(fire: any, items: any[]): string {
  const item = items.find((i) => i.id === fire.tracked_item_id);
  if (!item) return '';
  const meta = (item.metadata ?? {}) as Record<string, any>;
  switch (item.category) {
    case 'medication':
      return [
        meta.drug_name,
        meta.dosage,
        meta.with_food ? '· with food' : undefined,
      ]
        .filter(Boolean)
        .join(' ');
    case 'water':
      return meta.glass_size_ml ? `${meta.glass_size_ml} ml` : '';
    case 'workout':
      return [
        meta.workout_type,
        meta.duration_minutes ? `${meta.duration_minutes} min` : undefined,
      ]
        .filter(Boolean)
        .join(' · ');
    case 'meal':
      return meta.meal_name ?? '';
    case 'custom':
      return meta.notes ?? '';
    default:
      return '';
  }
}

interface MeasurementGroup {
  type: string;
  label: string;
  unit: string;
  latest: number;
  sparklineData: number[];
  trend: '▲' | '▼' | '—';
  delta: number;
}

function computeMeasurementGroups(measurements: any[]): MeasurementGroup[] {
  const byType: Record<string, any[]> = {};
  measurements.forEach((m) => {
    if (!byType[m.type]) byType[m.type] = [];
    byType[m.type].push(m);
  });

  return Object.entries(byType)
    .map(([type, readings]) => {
      const sorted = [...readings].sort(
        (a, b) => new Date(a.measured_at).getTime() - new Date(b.measured_at).getTime()
      );
      const values = sorted.map((m) => parseFloat(String(m.value)));
      const latest = values[values.length - 1];
      const sparklineData = values.slice(-14);
      const avg = values.reduce((s, v) => s + v, 0) / values.length;
      const delta = latest - avg;
      const trend: '▲' | '▼' | '—' =
        Math.abs(delta) < 0.5 ? '—' : delta > 0 ? '▲' : '▼';
      return {
        type,
        label: getMeasurementLabel(type),
        unit: getMeasurementUnit(type),
        latest,
        sparklineData,
        trend,
        delta: Math.abs(delta),
      };
    })
    .slice(0, 3);
}

function computeWeekSummary(items: any[], logs: any[]): string[] {
  const lines: string[] = [];

  const medItems = items.filter((i) => i.category === 'medication');
  if (medItems.length > 0) {
    const daysTaken = new Set(
      logs
        .filter((l) => l.action === 'taken')
        .map((l) => l.occurred_at.slice(0, 10))
    ).size;
    lines.push(daysTaken === 7 ? 'No missed medications' : `Medications taken on ${daysTaken} of 7 days`);
  }

  const waterItems = items.filter((i) => i.category === 'water');
  if (waterItems.length > 0) {
    const daysLogged = new Set(
      logs
        .filter((l) => l.action === 'logged_value')
        .map((l) => l.occurred_at.slice(0, 10))
    ).size;
    lines.push(`${daysLogged} of 7 days on water goal`);
  }

  const measurementLogs = logs.filter((l) => l.action === 'logged_value');
  if (measurementLogs.length > 0 && waterItems.length === 0) {
    lines.push(`${measurementLogs.length} readings logged this week`);
  }

  return lines.slice(0, 3);
}

// ── section label ─────────────────────────────────────────────────────────────

function SectionLabel({ label }: { label: string }) {
  return (
    <Text
      variant="label"
      color="mist"
      style={styles.sectionLabel}
    >
      {label}
    </Text>
  );
}

// ── timeline item ─────────────────────────────────────────────────────────────

interface TimelineItemProps {
  fire: any;
  item: any;
  isLogged: boolean;
  onPress: () => void;
}

function TimelineItem({ fire, item, isLogged, onPress }: TimelineItemProps) {
  const fireDate = parseISO(fire.fire_at);
  const timeStr = format(fireDate, 'HH:mm');
  const isPast = fireDate < new Date();
  const isOverdue = isPast && !isLogged;
  const category = item?.category ?? 'custom';
  const accentColor = CATEGORY_COLORS[category] ?? tokens.mist;
  const subtitle = item ? getFireSubtitle(fire, [item]) : '';
  const rawTitle: string = (fire.payload as any)?.body ?? item?.name ?? '';
  const meta = (item?.metadata ?? {}) as Record<string, unknown>;
  const title = rawTitle.includes('{') ? resolveTemplate(rawTitle, meta) : rawTitle;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.timelineItem, pressed && { opacity: 0.75 }]}
      accessibilityLabel={`${title}, scheduled at ${timeStr}${isLogged ? ', logged' : isOverdue ? ', overdue' : ''}`}
      accessibilityRole="button"
    >
      {/* Left edge accent bar */}
      <View style={[styles.accentBar, { backgroundColor: accentColor }]} />

      {/* Time */}
      <Text
        variant="mono"
        color={isLogged ? 'mist' : isOverdue ? 'warning' : 'slate'}
        style={styles.timeCol}
      >
        {timeStr}
      </Text>

      {/* Icon */}
      <View style={styles.iconCol}>
        <CategoryIcon category={category} size={18} />
      </View>

      {/* Title + subtitle */}
      <View style={styles.contentCol}>
        <Text
          variant="body"
          color={isLogged ? 'mist' : 'ink'}
          style={[
            { fontFamily: 'GeistSans-Medium' },
            isLogged && { textDecorationLine: 'line-through' },
          ]}
          numberOfLines={1}
        >
          {title}
        </Text>
        {subtitle ? (
          <Text variant="bodySmall" color="mist" numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      {/* Status indicator */}
      <View style={styles.statusCol}>
        {isLogged ? (
          <Check size={16} color={tokens.positive} strokeWidth={2} />
        ) : (
          <View
            style={[
              styles.statusCircle,
              { borderColor: isOverdue ? tokens.warning : tokens.mist },
            ]}
          />
        )}
      </View>
    </Pressable>
  );
}

// ── measurement card ──────────────────────────────────────────────────────────

function MeasurementCard({ group }: { group: MeasurementGroup }) {
  const trendColor = group.trend === '—' ? tokens.mist : tokens.positive;
  const valueStr =
    group.latest >= 100
      ? group.latest.toFixed(0)
      : group.latest.toFixed(1);

  return (
    <Pressable
      onPress={() => router.push(`/measurement/${group.type}` as any)}
      style={({ pressed }) => [styles.measurementCard, pressed && { opacity: 0.75 }]}
      accessibilityLabel={`${group.label}: ${valueStr} ${group.unit}, trend ${group.trend === '—' ? 'stable' : group.trend === '▲' ? 'rising' : 'falling'}`}
      accessibilityRole="button"
    >
      <Text
        variant="label"
        color="mist"
        style={styles.measurementLabel}
      >
        {group.label.toUpperCase()}
      </Text>

      <View style={styles.measurementValueRow}>
        <Text
          variant="displayL"
          color="ink"
          style={styles.measurementValue}
        >
          {valueStr}
        </Text>
        <Text variant="body" color="mist" style={styles.measurementUnit}>
          {group.unit}
        </Text>
      </View>

      <View style={styles.trendRow}>
        <Text variant="mono" style={{ fontSize: 12, color: trendColor }}>
          {group.trend}
        </Text>
        {group.trend !== '—' && (
          <Text variant="mono" style={{ fontSize: 12, color: trendColor, marginLeft: 2 }}>
            {group.delta.toFixed(1)}
          </Text>
        )}
        <Text variant="caption" color="mist" style={{ marginLeft: tokens.s4 }}>
          vs 30d avg
        </Text>
      </View>

      <View style={styles.sparklineContainer}>
        <Sparkline
          data={group.sparklineData}
          width={128}
          height={30}
          strokeColor={tokens.chartLine}
          strokeWidth={1.5}
        />
      </View>
    </Pressable>
  );
}

// ── week summary row ──────────────────────────────────────────────────────────

function WeekSummaryRow({ text }: { text: string }) {
  return (
    <View style={styles.weekRow}>
      <View style={styles.weekDot} />
      <Text variant="body" color="slate" style={{ flex: 1 }}>
        {text}
      </Text>
    </View>
  );
}

// ── main screen ───────────────────────────────────────────────────────────────

export default function TodayScreen() {
  const greeting = useGreeting();
  const today = format(new Date(), 'EEEE, d MMMM');
  const permStatus = usePermissionStatus();

  const [sheetFire, setSheetFire] = useState<any | null>(null);
  // Optimistic: fire keys logged this session (cleared on page refresh; server data below takes over)
  const [optimisticKeys, setOptimisticKeys] = useState<Set<string>>(new Set());
  const [refreshing, setRefreshing] = useState(false);

  const qc = useQueryClient();
  const { data: fires = [], isLoading: firesLoading } = useUpcomingReminders(18);
  const { data: items = [] } = useTrackedItems();
  const { data: measurements = [] } = useRecentMeasurements();
  const { data: weekLogs = [] } = useWeekLogs();

  // Derive server-confirmed logged keys from week logs — persists across refreshes.
  // Two indexes: by fire_key (precise) and by tracked_item_id+date (fallback for
  // water/custom items whose log entries may have fire_key: null).
  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const { serverLoggedKeys, loggedItemDates } = useMemo(() => {
    const keys = new Set<string>();
    const itemDates = new Set<string>(); // "itemId:date"
    (weekLogs as any[]).forEach((log: any) => {
      if (log.fire_key) keys.add(log.fire_key);
      if (log.tracked_item_id && log.occurred_at) {
        const date = (log.occurred_at as string).slice(0, 10);
        itemDates.add(`${log.tracked_item_id}:${date}`);
      }
    });
    return { serverLoggedKeys: keys, loggedItemDates: itemDates };
  }, [weekLogs]);

  // Merge server data + optimistic session updates
  const loggedFireKeys = useMemo(
    () => new Set([...serverLoggedKeys, ...optimisticKeys]),
    [serverLoggedKeys, optimisticKeys]
  );

  // Returns true if a fire has been logged — by fire_key, optimistic key, or item+date fallback
  const isFireLogged = (fire: any): boolean => {
    if (fire.fire_key && loggedFireKeys.has(fire.fire_key)) return true;
    return loggedItemDates.has(`${fire.tracked_item_id}:${todayStr}`);
  };

  const logEntry = useLogEntry();

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.allSettled([
      qc.invalidateQueries({ queryKey: ['upcoming-reminders'] }),
      qc.invalidateQueries({ queryKey: ['tracked-items'] }),
      qc.invalidateQueries({ queryKey: ['measurements-recent-30d'] }),
      qc.invalidateQueries({ queryKey: ['logs-week'] }),
    ]);
    setRefreshing(false);
  };

  const measurementGroups = useMemo(
    () => computeMeasurementGroups(measurements as any[]),
    [measurements]
  );

  const weekSummary = useMemo(
    () => computeWeekSummary(items as any[], weekLogs as any[]),
    [items, weekLogs]
  );

  function handleActionPress(actionId: string) {
    if (!sheetFire) return;
    const fire = sheetFire;
    setSheetFire(null);

    // Optimistic: mark as logged immediately
    if (fire.fire_key) {
      setOptimisticKeys((prev) => new Set([...prev, fire.fire_key]));
    }

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    logEntry.mutate(
      {
        tracked_item_id: fire.tracked_item_id,
        action: ACTION_API[actionId] ?? actionId,
        occurred_at: new Date().toISOString(),
        fire_key: fire.fire_key,
      },
      {
        onSuccess: () => {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          // Sync server state so checkmarks survive refresh
          qc.invalidateQueries({ queryKey: ['logs-week'] });
        },
        onError: () => {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          // Roll back optimistic key on failure
          if (fire.fire_key) {
            setOptimisticKeys((prev) => {
              const next = new Set(prev);
              next.delete(fire.fire_key);
              return next;
            });
          }
        },
      }
    );
  }

  const sheetItem = sheetFire
    ? (items as any[]).find((i) => i.id === sheetFire.tracked_item_id)
    : null;

  const sheetActions: SheetAction[] = sheetFire
    ? (((sheetFire.payload as any)?.actions ?? []) as string[]).map((a) => ({
        id: a,
        label: ACTION_LABELS[a] ?? a,
        variant: a === 'taken' || a === 'logged_value' ? 'primary' : a === 'skipped' ? 'destructive' : 'default',
      }))
    : [];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={tokens.mist}
          />
        }
      >
        {/* ── Header ── */}
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text variant="displayM" color="ink">{greeting}</Text>
            <Text variant="mono" color="mist" style={styles.dateText}>{today}</Text>
          </View>
          <Pressable
            onPress={() => router.push('/(tabs)/settings')}
            hitSlop={12}
            accessibilityLabel="Open settings"
            accessibilityRole="button"
          >
            <Settings size={22} color={tokens.slate} strokeWidth={1.5} />
          </Pressable>
        </View>

        {/* ── Permission denied banner ── */}
        {permStatus === 'denied' && (
          <Pressable
            style={styles.permBanner}
            onPress={() => Linking.openSettings()}
            accessibilityLabel="Notifications are disabled. Tap to open Settings."
            accessibilityRole="button"
          >
            <BellOff size={15} color={tokens.warning} strokeWidth={1.5} />
            <Text variant="bodySmall" color="warning" style={{ flex: 1 }}>
              Notifications are disabled — tap to enable in Settings
            </Text>
          </Pressable>
        )}

        {/* ── Today section ── */}
        <View style={styles.section}>
          <SectionLabel label="TODAY" />
          {firesLoading ? (
            <SkeletonTimeline />
          ) : fires.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text variant="h2" color="ink" style={{ textAlign: 'center', marginBottom: tokens.s8 }}>
                Nothing scheduled for today
              </Text>
              <Text variant="body" color="slate" style={{ textAlign: 'center', marginBottom: tokens.s24 }}>
                Add your first reminder from the Library tab
              </Text>
              <Pressable
                onPress={() => router.push('/(tabs)/library')}
                style={styles.ghostButton}
              >
                <Text variant="body" color="slate">Open Library</Text>
              </Pressable>
            </View>
          ) : (
            <View style={styles.timeline}>
              {(fires as any[]).map((fire) => {
                const item = (items as any[]).find((i) => i.id === fire.tracked_item_id);
                return (
                  <TimelineItem
                    key={fire.fire_key}
                    fire={fire}
                    item={item}
                    isLogged={isFireLogged(fire)}
                    onPress={() => {
                      if (!isFireLogged(fire)) setSheetFire(fire);
                    }}
                  />
                );
              })}
            </View>
          )}
        </View>

        {/* ── Recent measurements ── */}
        {measurementGroups.length > 0 && (
          <View style={styles.section}>
            <SectionLabel label="RECENT" />
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.measurementScroll}
            >
              {measurementGroups.map((group) => (
                <MeasurementCard key={group.type} group={group} />
              ))}
            </ScrollView>
          </View>
        )}

        {/* ── This week ── */}
        {weekSummary.length > 0 && (
          <View style={styles.section}>
            <SectionLabel label="THIS WEEK" />
            <Card style={styles.weekCard}>
              {weekSummary.map((line, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <View style={styles.weekSeparator} />}
                  <WeekSummaryRow text={line} />
                </React.Fragment>
              ))}
            </Card>
          </View>
        )}
      </ScrollView>

      {/* ── Action sheet ── */}
      <ActionSheet
        visible={sheetFire !== null}
        title={(sheetFire?.payload as any)?.body}
        subtitle={sheetItem ? getFireSubtitle(sheetFire, [sheetItem]) : undefined}
        actions={sheetActions}
        onAction={handleActionPress}
        onClose={() => setSheetFire(null)}
      />
    </SafeAreaView>
  );
}

// ── skeleton ──────────────────────────────────────────────────────────────────

function SkeletonTimeline() {
  return (
    <View style={styles.timeline}>
      {[0, 1, 2].map((i) => (
        <View key={i} style={[styles.timelineItem, styles.skeletonItem]}>
          <View style={[styles.skeletonBar, { width: 40 }]} />
          <View style={[styles.skeletonBar, { width: 18, height: 18, borderRadius: 9 }]} />
          <View style={{ flex: 1, gap: tokens.s4 }}>
            <View style={[styles.skeletonBar, { width: '60%' }]} />
            <View style={[styles.skeletonBar, { width: '40%', height: 12 }]} />
          </View>
        </View>
      ))}
    </View>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: tokens.bone,
  },
  scroll: {
    paddingBottom: tokens.s48,
  },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s24,
    paddingBottom: tokens.s8,
  },
  dateText: {
    marginTop: tokens.s4,
  },

  // Permission banner
  permBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.s8,
    marginHorizontal: tokens.s20,
    marginTop: tokens.s8,
    padding: tokens.s12,
    backgroundColor: `${tokens.warning}18`,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: `${tokens.warning}40`,
  },

  // Sections
  section: {
    marginTop: tokens.s32,
    paddingHorizontal: tokens.s20,
  },
  sectionLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1.2,
    marginBottom: tokens.s16,
  },

  // Timeline
  timeline: {
    gap: 12,
  },
  timelineItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    overflow: 'hidden',
    minHeight: 64,
  },
  accentBar: {
    width: 2,
    alignSelf: 'stretch',
  },
  timeCol: {
    width: 52,
    paddingVertical: 14,
    paddingLeft: tokens.s12,
    fontSize: 13,
  },
  iconCol: {
    width: 28,
    alignItems: 'center',
  },
  contentCol: {
    flex: 1,
    paddingVertical: 14,
    paddingRight: tokens.s8,
    gap: 2,
  },
  statusCol: {
    width: 40,
    alignItems: 'center',
    justifyContent: 'center',
    paddingRight: tokens.s12,
  },
  statusCircle: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 1.5,
  },

  // Empty today
  emptyCard: {
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    padding: tokens.s32,
    alignItems: 'center',
  },
  ghostButton: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: tokens.s8,
    paddingHorizontal: tokens.s24,
  },

  // Measurements
  measurementScroll: {
    gap: 12,
    paddingRight: tokens.s20,
  },
  measurementCard: {
    width: 160,
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    padding: tokens.s16,
  },
  measurementLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: tokens.s8,
  },
  measurementValueRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: tokens.s4,
  },
  measurementValue: {
    fontSize: 36,
    lineHeight: 40,
  },
  measurementUnit: {
    marginBottom: 4,
  },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: tokens.s4,
    marginBottom: tokens.s8,
  },
  sparklineContainer: {
    marginTop: tokens.s4,
  },

  // Week summary
  weekCard: {
    padding: tokens.s16,
    gap: 0,
  },
  weekRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: tokens.s8,
    gap: tokens.s12,
  },
  weekDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: tokens.positive,
    flexShrink: 0,
  },
  weekSeparator: {
    height: 1,
    backgroundColor: tokens.hairline,
    marginHorizontal: -tokens.s16,
  },

  // Skeleton
  skeletonItem: {
    paddingVertical: 14,
    paddingHorizontal: tokens.s12,
    gap: tokens.s12,
  },
  skeletonBar: {
    height: 14,
    borderRadius: tokens.radii.card,
    backgroundColor: tokens.hairline,
  },
});
