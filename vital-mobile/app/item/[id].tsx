import React from 'react';
import { Alert, Platform, Pressable, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, Pencil } from 'lucide-react-native';
import { format, parseISO } from 'date-fns';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Card } from '../../src/components/Card';
import { Button } from '../../src/components/Button';
import { StatusBadge } from '../../src/components/StatusBadge';
import {
  useTrackedItem,
  useItemLogs,
  usePatchTrackedItem,
  useDiscontinueTrackedItem,
} from '../../src/api/queries';
import { formatScheduleSummary, estimateExpectedFires } from '../../src/utils/schedule';
import { CATEGORY_LABELS, ACTION_DISPLAY, getCategoryColor } from '../../src/utils/itemHelpers';

export default function TrackedItemDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: item, isLoading } = useTrackedItem(id);
  const { data: logs = [] } = useItemLogs(id, 30);
  const patchItem = usePatchTrackedItem();
  const discontinue = useDiscontinueTrackedItem();

  if (isLoading || !item) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
          </Pressable>
        </View>
        <SkeletonDetail />
      </SafeAreaView>
    );
  }

  const anyItem = item as any;
  const category: string = anyItem.category;
  const status: string = anyItem.status;
  const reminders: any[] = anyItem.reminders ?? [];
  const recentLogs = (logs as any[]).slice(0, 10);
  const accentColor = getCategoryColor(category);

  // Adherence calculation
  const totalTaken = (logs as any[]).filter(
    (l) => l.action === 'taken' || l.action === 'logged_value'
  ).length;
  const expectedFires = reminders.reduce(
    (sum, r) => sum + estimateExpectedFires(r.schedule, 30),
    0
  );
  const adherencePct =
    expectedFires > 0 ? Math.min(100, Math.round((totalTaken / expectedFires) * 100)) : null;

  const handlePauseResume = async () => {
    const newStatus = status === 'active' ? 'paused' : 'active';
    await patchItem.mutateAsync({ id, status: newStatus });
  };

  const handleDiscontinue = async () => {
    const confirmed = Platform.OS === 'web'
      ? window.confirm("Discontinue item? This will deactivate all reminders. The history is kept. You can't undo this.")
      : await new Promise<boolean>((resolve) =>
          Alert.alert(
            'Discontinue item?',
            "This will deactivate all reminders. The history is kept. You can't undo this.",
            [
              { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
              { text: 'Discontinue', style: 'destructive', onPress: () => resolve(true) },
            ]
          )
        );
    if (!confirmed) return;
    await discontinue.mutateAsync(id);
    router.replace('/(tabs)/library');
  };

  const editRoute = `/item/new/${category === 'vital_check' ? 'vital_check' : category}?itemId=${id}`;

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
        <Pressable onPress={() => router.push(editRoute as any)} hitSlop={12}>
          <Pencil size={20} color={tokens.slate} strokeWidth={1.5} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* Item name + category badge */}
        <View style={styles.titleBlock}>
          <View style={[styles.accentLine, { backgroundColor: accentColor }]} />
          <Text variant="displayM" color="ink">{anyItem.name}</Text>
          <View style={styles.badgeRow}>
            <StatusBadge
              label={(CATEGORY_LABELS[category] ?? category).toUpperCase()}
              variant={status === 'active' ? 'positive' : status === 'paused' ? 'warning' : 'neutral'}
            />
            {status !== 'active' && (
              <StatusBadge
                label={status.toUpperCase()}
                variant={status === 'paused' ? 'warning' : 'neutral'}
              />
            )}
          </View>
        </View>

        {/* Adherence stat */}
        {adherencePct !== null && (
          <Card style={styles.adherenceCard}>
            <Text variant="label" color="mist" style={styles.sectionLabel}>
              ADHERENCE (LAST 30 DAYS)
            </Text>
            <View style={styles.adherenceRow}>
              <Text variant="displayL" color="ink">{adherencePct}%</Text>
              <Text variant="body" color="slate" style={styles.adherenceDetail}>
                {totalTaken} of ~{Math.round(expectedFires)} expected
              </Text>
            </View>
          </Card>
        )}

        {/* Reminders */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>REMINDERS</Text>
          {reminders.length === 0 ? (
            <Text variant="bodySmall" color="mist">No reminders set.</Text>
          ) : (
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {reminders.map((rem, idx) => (
                <React.Fragment key={rem.id}>
                  {idx > 0 && <View style={styles.divider} />}
                  <View style={styles.reminderRow}>
                    <View style={styles.reminderDot} />
                    <View style={{ flex: 1 }}>
                      <Text variant="body" color="ink">
                        {formatScheduleSummary(rem.schedule)}
                      </Text>
                      {rem.message_template ? (
                        <Text variant="bodySmall" color="mist">
                          "{rem.message_template}"
                        </Text>
                      ) : null}
                    </View>
                    <StatusBadge
                      label={rem.active ? 'Active' : 'Off'}
                      variant={rem.active ? 'positive' : 'neutral'}
                    />
                  </View>
                </React.Fragment>
              ))}
            </Card>
          )}
        </View>

        {/* Recent activity */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>RECENT ACTIVITY</Text>
          {recentLogs.length === 0 ? (
            <Text variant="bodySmall" color="mist">No activity yet.</Text>
          ) : (
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {recentLogs.map((log: any, idx: number) => {
                const display = ACTION_DISPLAY[log.action] ?? { label: log.action, color: 'slate' as const };
                const ts = format(parseISO(log.occurred_at), 'd MMM, HH:mm');
                return (
                  <React.Fragment key={log.id}>
                    {idx > 0 && <View style={styles.divider} />}
                    <View style={styles.logRow}>
                      <Text variant="mono" color="mist" style={styles.logTime}>{ts}</Text>
                      <Text variant="body" color={display.color}>{display.label}</Text>
                    </View>
                  </React.Fragment>
                );
              })}
            </Card>
          )}
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          {status !== 'discontinued' && (
            <>
              <Button
                onPress={handlePauseResume}
                variant="secondary"
                style={styles.actionBtn}
                disabled={patchItem.isPending}
              >
                {status === 'active' ? 'Pause reminders' : 'Resume reminders'}
              </Button>
              <Button
                onPress={handleDiscontinue}
                variant="ghost"
                style={styles.actionBtn}
                disabled={discontinue.isPending}
              >
                Discontinue
              </Button>
            </>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function SkeletonDetail() {
  return (
    <View style={[styles.content, { gap: tokens.s16 }]}>
      {[120, 200, 100].map((w, i) => (
        <View key={i} style={[styles.sk, { width: `${w}%`.slice(0, 4), height: i === 1 ? 120 : 20 }]} />
      ))}
    </View>
  );
}

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
    paddingTop: tokens.s16,
    paddingBottom: tokens.s48,
    gap: tokens.s32,
  },
  titleBlock: { gap: tokens.s8 },
  accentLine: {
    width: 24,
    height: 3,
    borderRadius: 2,
    marginBottom: tokens.s4,
  },
  badgeRow: { flexDirection: 'row', gap: tokens.s8, marginTop: tokens.s4 },

  adherenceCard: { padding: tokens.s16 },
  adherenceRow: { flexDirection: 'row', alignItems: 'flex-end', gap: tokens.s12 },
  adherenceDetail: { marginBottom: tokens.s8 },

  section: { gap: tokens.s12 },
  sectionLabel: { letterSpacing: 1, textTransform: 'uppercase' },

  divider: { height: 1, backgroundColor: tokens.hairline },

  reminderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.s16,
    gap: tokens.s12,
  },
  reminderDot: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: tokens.positive, flexShrink: 0,
  },

  logRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.s12,
    paddingHorizontal: tokens.s16,
    gap: tokens.s12,
  },
  logTime: { width: 100 },

  actions: { gap: tokens.s12 },
  actionBtn: {},

  sk: { borderRadius: tokens.radii.card, backgroundColor: tokens.hairline },
});
