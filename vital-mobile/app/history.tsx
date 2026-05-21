import { DateInput } from '../src/components/DateInput';
import React, { useState, useMemo } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { format, parseISO, subDays } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';

import { tokens } from '../src/theme/tokens';
import { Text } from '../src/components/Text';
import { EmptyState } from '../src/components/EmptyState';
import { useTrackedItems, useAllLogs } from '../src/api/queries';

// ── filter chips ──────────────────────────────────────────────────────────────

const FILTER_CHIPS = [
  { key: 'all', label: 'All' },
  { key: 'medication', label: 'Medications' },
  { key: 'water', label: 'Water' },
  { key: 'workout', label: 'Workouts' },
  { key: 'meal', label: 'Meals' },
  { key: 'custom', label: 'Custom' },
] as const;

type FilterKey = typeof FILTER_CHIPS[number]['key'];

// ── action badge colors ───────────────────────────────────────────────────────

function actionColor(action: string): string {
  switch (action) {
    case 'taken':        return tokens.positive;
    case 'skipped':      return tokens.warning;
    case 'snoozed':      return tokens.slate;
    case 'logged_value': return tokens.ink;
    case 'acknowledged': return tokens.positive;
    default:             return tokens.mist;
  }
}

function actionLabel(action: string): string {
  switch (action) {
    case 'taken':        return 'Taken';
    case 'skipped':      return 'Skipped';
    case 'snoozed':      return 'Snoozed';
    case 'logged_value': return 'Logged';
    case 'acknowledged': return 'Done';
    default:             return action;
  }
}

// ── log row ───────────────────────────────────────────────────────────────────

interface LogRowProps {
  log: any;
  itemName: string;
}

function LogRow({ log, itemName }: LogRowProps) {
  const date = parseISO(log.occurred_at);
  const timeStr = format(date, 'HH:mm');
  const dateStr = format(date, 'd MMM');
  const color = actionColor(log.action);
  const label = actionLabel(log.action);

  return (
    <View style={styles.logRow}>
      <View style={styles.logTimeCol}>
        <Text variant="mono" color="slate" style={styles.logTime}>{timeStr}</Text>
        <Text variant="mono" color="mist" style={styles.logDate}>{dateStr}</Text>
      </View>
      <Text variant="body" color="ink" style={styles.logName} numberOfLines={1}>
        {itemName}
      </Text>
      <View style={[styles.actionBadge, { borderColor: color }]}>
        <Text variant="caption" style={{ color }}>
          {label}
        </Text>
      </View>
    </View>
  );
}

// ── main screen ───────────────────────────────────────────────────────────────

export default function HistoryScreen() {
  const qc = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');

  const [fromDate, setFromDate] = useState<Date>(() => subDays(new Date(), 30));
  const [toDate, setToDate] = useState<Date>(() => new Date());

  const { data: rawItems = [] } = useTrackedItems();
  const items = rawItems as any[];

  const idToCategoryMap = useMemo(() => {
    const map: Record<string, string> = {};
    items.forEach((i: any) => { map[i.id] = i.category; });
    return map;
  }, [items]);

  const idToNameMap = useMemo(() => {
    const map: Record<string, string> = {};
    items.forEach((i: any) => { map[i.id] = i.name; });
    return map;
  }, [items]);

  const { data: rawLogs = [] } = useAllLogs(
    fromDate.toISOString(),
    toDate.toISOString()
  );
  const logs = rawLogs as any[];

  const filteredLogs = useMemo(() => {
    let result = [...logs];
    if (activeFilter !== 'all') {
      result = result.filter(
        (l) => idToCategoryMap[l.tracked_item_id] === activeFilter
      );
    }
    // Sort newest first
    return result.sort(
      (a, b) =>
        new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
    );
  }, [logs, activeFilter, idToCategoryMap]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await qc.invalidateQueries({ queryKey: ['logs-all'] });
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
        <Text variant="h1" color="ink" style={styles.title}>History</Text>
        <View style={{ width: 22 }} />
      </View>

      {/* Date range row */}
      <View style={styles.dateRow}>
        <View style={styles.dateField}>
          <DateInput label="From" value={fromDate} onChange={setFromDate} maximumDate={toDate} />
        </View>
        <Text variant="caption" color="mist" style={styles.dateSep}>—</Text>
        <View style={styles.dateField}>
          <DateInput label="To" value={toDate} onChange={setToDate} minimumDate={fromDate} maximumDate={new Date()} />
        </View>
      </View>

      {/* Filter chips */}
      <FlatList
        horizontal
        data={FILTER_CHIPS as unknown as Array<{ key: FilterKey; label: string }>}
        keyExtractor={(item) => item.key}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsContent}
        style={styles.chips}
        renderItem={({ item: chip }) => (
          <Pressable
            style={[
              styles.chip,
              activeFilter === chip.key && styles.chipActive,
            ]}
            onPress={() => setActiveFilter(chip.key)}
          >
            <Text
              variant="bodySmall"
              color={activeFilter === chip.key ? 'ink' : 'slate'}
              style={activeFilter === chip.key ? { fontFamily: 'GeistSans-Medium' } : undefined}
            >
              {chip.label}
            </Text>
          </Pressable>
        )}
      />

      {/* Log list */}
      <FlatList
        data={filteredLogs}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={tokens.mist}
          />
        }
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        ListEmptyComponent={
          <View style={styles.emptyWrapper}>
            <EmptyState
              title="No entries"
              body={
                activeFilter === 'all'
                  ? 'No logs found for this date range.'
                  : `No ${activeFilter} logs found for this date range.`
              }
            />
          </View>
        }
        renderItem={({ item }) => (
          <LogRow
            log={item}
            itemName={idToNameMap[item.tracked_item_id] ?? 'Unknown'}
          />
        )}
      />
    </SafeAreaView>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s8,
  },
  title: { flex: 1, textAlign: 'center' },

  // Date range
  dateRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: tokens.s20,
    paddingVertical: tokens.s8,
    gap: tokens.s12,
  },
  dateField: { flex: 1, gap: tokens.s4 },
  dateSep: { marginTop: tokens.s20 },
  dateBtn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    paddingVertical: tokens.s8,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },

  // Filter chips
  chips: { flexGrow: 0 },
  chipsContent: {
    paddingHorizontal: tokens.s20,
    paddingBottom: tokens.s8,
    gap: tokens.s8,
    flexDirection: 'row',
  },
  chip: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: 6,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  chipActive: {
    borderColor: tokens.ink,
    backgroundColor: tokens.divider,
  },

  // List
  listContent: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s8,
    paddingBottom: tokens.s48,
  },
  separator: { height: 1, backgroundColor: tokens.hairline },
  emptyWrapper: { marginTop: tokens.s32 },

  // Log row
  logRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: tokens.s12,
    backgroundColor: tokens.paper,
    gap: tokens.s12,
    paddingHorizontal: tokens.s12,
    borderRadius: tokens.radii.card,
  },
  logTimeCol: {
    width: 44,
    alignItems: 'flex-end',
    gap: 2,
  },
  logTime: { fontSize: 13 },
  logDate: { fontSize: 11 },
  logName: { flex: 1 },
  actionBadge: {
    borderWidth: 1,
    borderRadius: tokens.radii.button,
    paddingVertical: 3,
    paddingHorizontal: tokens.s8,
  },
});
