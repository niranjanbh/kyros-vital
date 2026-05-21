import React, { useState, useMemo } from 'react';
import {
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Plus, Pill, Droplet, Dumbbell, Utensils, Activity, Tag, FlaskConical } from 'lucide-react-native';
import { format, parseISO } from 'date-fns';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { ListItem } from '../../src/components/ListItem';
import { Button } from '../../src/components/Button';
import { useTrackedItems, useLabReports } from '../../src/api/queries';
import {
  CATEGORY_LABELS,
  FILTER_CHIPS,
  getCategoryColor,
  getItemSubtitle,
} from '../../src/utils/itemHelpers';

function CategoryIcon({ category, size = 18 }: { category: string; size?: number }) {
  const color = getCategoryColor(category);
  const p = { size, color, strokeWidth: 1.5 };
  switch (category) {
    case 'medication':  return <Pill {...p} />;
    case 'water':       return <Droplet {...p} />;
    case 'workout':     return <Dumbbell {...p} />;
    case 'meal':        return <Utensils {...p} />;
    case 'vital_check': return <Activity {...p} />;
    default:            return <Tag {...p} />;
  }
}

export default function LibraryScreen() {
  const qc = useQueryClient();
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [refreshing, setRefreshing] = useState(false);
  const { data: rawItems = [], isLoading } = useTrackedItems();
  const { data: rawReports = [] } = useLabReports();
  const items = rawItems as any[];
  const reports = rawReports as any[];

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['tracked-items'] }),
      qc.invalidateQueries({ queryKey: ['lab-reports'] }),
    ]);
    setRefreshing(false);
  };

  const filteredItems = useMemo(() => {
    const active = items.filter((i) => i.status !== 'discontinued');
    if (activeFilter === 'all') return active;
    return active.filter((i) => i.category === activeFilter);
  }, [items, activeFilter]);

  const sections = useMemo(() => {
    if (activeFilter !== 'all') {
      return [{ category: activeFilter, items: filteredItems }];
    }
    const order = ['medication', 'water', 'workout', 'meal', 'vital_check', 'custom'];
    const grouped: Record<string, any[]> = {};
    filteredItems.forEach((item) => {
      if (!grouped[item.category]) grouped[item.category] = [];
      grouped[item.category].push(item);
    });
    return order
      .filter((cat) => grouped[cat]?.length > 0)
      .map((cat) => ({ category: cat, items: grouped[cat] }));
  }, [filteredItems, activeFilter]);

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Text variant="displayM" color="ink">Library</Text>
        <Pressable onPress={() => router.push('/item/new')} hitSlop={12}>
          <Plus size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
      </View>

      {/* Filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsContent}
        style={styles.chips}
      >
        {FILTER_CHIPS.map((chip) => (
          <Pressable
            key={chip.key}
            style={({ pressed }) => [styles.chip, pressed && { opacity: 0.7 }]}
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
        ))}
      </ScrollView>

      {/* Main list */}
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={tokens.mist}
          />
        }
      >
        {isLoading ? (
          <SkeletonList />
        ) : filteredItems.length === 0 ? (
          <EmptyLibrary onAdd={() => router.push('/item/new')} />
        ) : (
          sections.map(({ category, items: sItems }) => (
            <View key={category} style={styles.section}>
              {activeFilter === 'all' && (
                <Text variant="label" color="mist" style={styles.sectionLabel}>
                  {(CATEGORY_LABELS[category] ?? category).toUpperCase()}
                </Text>
              )}
              <View style={styles.card}>
                {sItems.map((item, idx) => (
                  <React.Fragment key={item.id}>
                    {idx > 0 && <View style={styles.divider} />}
                    <ListItem
                      title={item.name}
                      subtitle={getItemSubtitle(item)}
                      left={<CategoryIcon category={item.category} />}
                      onPress={() => router.push(`/item/${item.id}`)}
                    />
                  </React.Fragment>
                ))}
              </View>
            </View>
          ))
        )}

        {/* Lab Reports section — always shown regardless of filter */}
        {activeFilter === 'all' && (
          <View style={styles.section}>
            <View style={styles.labHeader}>
              <Text variant="label" color="mist" style={styles.sectionLabel}>LAB REPORTS</Text>
              <Pressable onPress={() => router.push('/lab/new')} hitSlop={8}>
                <Plus size={16} color={tokens.tealDeep} strokeWidth={1.5} />
              </Pressable>
            </View>
            {reports.length === 0 ? (
              <Pressable style={styles.labEmpty} onPress={() => router.push('/lab/new')}>
                <FlaskConical size={20} color={tokens.mist} strokeWidth={1.5} />
                <Text variant="bodySmall" color="mist">Upload your first lab report</Text>
              </Pressable>
            ) : (
              <View style={styles.card}>
                {reports.map((report: any, idx: number) => (
                  <React.Fragment key={report.id}>
                    {idx > 0 && <View style={styles.divider} />}
                    <LabReportRow report={report} />
                  </React.Fragment>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function EmptyLibrary({ onAdd }: { onAdd: () => void }) {
  return (
    <View style={styles.empty}>
      <Text variant="h2" color="ink" style={styles.emptyTitle}>No tracked items yet</Text>
      <Text variant="body" color="slate" style={styles.emptyBody}>
        Add medications, water goals, workouts, and more.
      </Text>
      <Button onPress={onAdd} variant="primary" style={styles.emptyBtn}>
        Add your first item
      </Button>
    </View>
  );
}

function SkeletonList() {
  return (
    <View style={styles.card}>
      {[0, 1, 2].map((i) => (
        <React.Fragment key={i}>
          {i > 0 && <View style={styles.divider} />}
          <View style={styles.skRow}>
            <View style={[styles.sk, { width: 20, height: 20, borderRadius: 10 }]} />
            <View style={{ flex: 1, gap: tokens.s4 }}>
              <View style={[styles.sk, { width: '55%' }]} />
              <View style={[styles.sk, { width: '35%', height: 12 }]} />
            </View>
          </View>
        </React.Fragment>
      ))}
    </View>
  );
}

function LabReportRow({ report }: { report: any }) {
  const parsed = (report.parsed ?? []) as any[];
  const flaggedCount = parsed.filter((t: any) => t.flag !== 'normal').length;
  const dateStr = format(parseISO(report.report_date), 'd MMM yyyy');

  return (
    <Pressable
      style={({ pressed }) => [styles.labRow, pressed && { backgroundColor: tokens.divider }]}
      onPress={() => router.push(`/lab/${report.id}`)}
    >
      <FlaskConical size={18} color={tokens.mist} strokeWidth={1.5} />
      <View style={{ flex: 1 }}>
        <Text variant="body" color="ink">{report.lab_name ?? 'Lab Report'}</Text>
        <Text variant="caption" color="mist">
          {dateStr} · {parsed.length} test{parsed.length !== 1 ? 's' : ''}
          {flaggedCount > 0 ? ` · ${flaggedCount} flagged` : ''}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s24,
    paddingBottom: tokens.s16,
  },
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
  scrollContent: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s48,
    gap: tokens.s24,
  },
  section: { gap: tokens.s8 },
  sectionLabel: { letterSpacing: 1, textTransform: 'uppercase' },
  card: {
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    overflow: 'hidden',
  },
  divider: { height: 1, backgroundColor: tokens.hairline },
  empty: { marginTop: tokens.s48, alignItems: 'center', paddingHorizontal: tokens.s32 },
  emptyTitle: { textAlign: 'center', marginBottom: tokens.s8 },
  emptyBody: { textAlign: 'center', marginBottom: tokens.s24 },
  emptyBtn: { minWidth: 200 },
  skRow: {
    flexDirection: 'row', alignItems: 'center',
    padding: tokens.s16, gap: tokens.s12,
  },
  sk: { height: 14, borderRadius: tokens.radii.card, backgroundColor: tokens.hairline },
  labHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  labEmpty: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.s8,
    padding: tokens.s16,
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    backgroundColor: tokens.paper,
  },
  labRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.s16,
    gap: tokens.s12,
  },
});
