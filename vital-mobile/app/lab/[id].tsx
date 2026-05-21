import React, { useState } from 'react';
import {
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, ExternalLink, Trash2 } from 'lucide-react-native';
import { format, parseISO } from 'date-fns';
import * as WebBrowser from 'expo-web-browser';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Card } from '../../src/components/Card';
import { ActionSheet } from '../../src/components/ActionSheet';
import { StatusBadge } from '../../src/components/StatusBadge';
import { useLabReport, useDeleteLabReport } from '../../src/api/queries';
import { getApiClient } from '../../src/api/client';
import { MEASUREMENT_META } from '../../src/charts/utils';

type Flag = 'normal' | 'low' | 'high' | 'critical';

type ParsedTest = {
  name: string;
  value: string;
  unit: string;
  ref_low?: number | null;
  ref_high?: number | null;
  flag: Flag;
};

const FLAG_TO_BADGE: Record<Flag, 'positive' | 'warning' | 'critical' | 'neutral'> = {
  normal:   'positive',
  low:      'warning',
  high:     'warning',
  critical: 'critical',
};

function detectMeasurementType(testName: string): string | null {
  const lower = testName.toLowerCase();
  if (lower.includes('hba1c') || lower.includes('hemoglobin a1c') || lower.includes(' a1c')) return 'hba1c';
  if (lower.includes('fasting glucose') || lower.includes('glucose')) return 'fasting_glucose';
  if (lower.includes('weight')) return 'weight';
  if (lower.includes('heart rate') || lower.includes('pulse')) return 'heart_rate';
  if (lower.includes('body temp') || lower.includes('temperature')) return 'body_temp';
  if (lower.includes('steps') || lower.includes('step count')) return 'steps';
  if (lower.includes('systolic')) return 'bp_systolic';
  if (lower.includes('diastolic')) return 'bp_diastolic';
  return null;
}

export default function LabReportDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: report, isLoading } = useLabReport(id ?? '');
  const deleteReport = useDeleteLabReport();
  const qc = useQueryClient();

  const [selectedTest, setSelectedTest] = useState<ParsedTest | null>(null);
  const [showActionSheet, setShowActionSheet] = useState(false);
  const [showTypeSheet, setShowTypeSheet] = useState(false);

  const createMeasurement = useMutation({
    mutationFn: async ({ type, value, unit, measuredAt }: {
      type: string; value: string; unit: string; measuredAt: string;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.POST('/v1/wellness/measurements/', {
        body: { type, value, unit, measured_at: measuredAt } as any,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['measurements'] });
      qc.invalidateQueries({ queryKey: ['measurements-recent-30d'] });
    },
  });

  const handleDelete = () => {
    Alert.alert('Delete report?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await deleteReport.mutateAsync(id ?? '');
          router.back();
        },
      },
    ]);
  };

  const handleLongPress = (test: ParsedTest) => {
    setSelectedTest(test);
    setShowActionSheet(true);
  };

  const handleConvert = async (measurementType: string) => {
    if (!selectedTest || !report) return;
    setShowTypeSheet(false);
    setShowActionSheet(false);
    const measuredAt = new Date(report.report_date + 'T00:00:00Z').toISOString();
    const meta = MEASUREMENT_META[measurementType];
    try {
      await createMeasurement.mutateAsync({
        type: measurementType,
        value: selectedTest.value,
        unit: selectedTest.unit || meta?.defaultUnit || '',
        measuredAt,
      });
      Alert.alert('Converted', `${selectedTest.name} added to ${meta?.label ?? measurementType}.`);
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Conversion failed.');
    }
  };

  const actionSheetActions = selectedTest
    ? (() => {
        const detected = detectMeasurementType(selectedTest.name);
        const actions: Parameters<typeof ActionSheet>[0]['actions'] = [];
        if (detected) {
          actions.push({
            id: `convert:${detected}`,
            label: `Convert to ${MEASUREMENT_META[detected]?.label ?? detected}`,
            variant: 'primary',
          });
        }
        actions.push({ id: 'choose_type', label: 'Choose measurement type…' });
        return actions;
      })()
    : [];

  const typeSheetActions = Object.entries(MEASUREMENT_META).map(([key, meta]) => ({
    id: `type:${key}`,
    label: meta.label,
  }));

  if (isLoading || !report) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
          </Pressable>
        </View>
        <View style={styles.loadingState}>
          <View style={[styles.sk, { width: 160, height: 28, marginBottom: tokens.s8 }]} />
          <View style={[styles.sk, { width: 100 }]} />
        </View>
      </SafeAreaView>
    );
  }

  const tests = (report.parsed ?? []) as ParsedTest[];
  const flaggedCount = tests.filter((t) => t.flag !== 'normal').length;
  const reportDateStr = format(parseISO(report.report_date), 'd MMM yyyy');

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
        <Pressable onPress={handleDelete} hitSlop={12} disabled={deleteReport.isPending}>
          <Trash2 size={20} color={tokens.critical} strokeWidth={1.5} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* Title block */}
        <View style={styles.titleBlock}>
          <Text variant="displayM" color="ink">
            {report.lab_name ?? 'Lab Report'}
          </Text>
          <Text variant="body" color="slate">{reportDateStr}</Text>
          {report.signed_url && (
            <Pressable
              style={styles.viewOriginalBtn}
              onPress={() => WebBrowser.openBrowserAsync(report.signed_url!)}
            >
              <ExternalLink size={14} color={tokens.tealDeep} strokeWidth={1.5} />
              <Text variant="bodySmall" color="tealDeep">View original</Text>
            </Pressable>
          )}
        </View>

        {/* Summary card */}
        <Card style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <Text variant="displayM" color="ink">{tests.length}</Text>
            <Text variant="body" color="mist" style={{ marginLeft: tokens.s4 }}>tests</Text>
            {flaggedCount > 0 && (
              <>
                <View style={styles.summaryDivider} />
                <Text variant="displayM" style={{ color: tokens.warning }}>{flaggedCount}</Text>
                <Text variant="body" color="mist" style={{ marginLeft: tokens.s4 }}>flagged</Text>
              </>
            )}
          </View>
          {report.note ? (
            <Text variant="bodySmall" color="slate" style={{ marginTop: tokens.s8 }}>
              {report.note}
            </Text>
          ) : null}
        </Card>

        {/* Tests table */}
        {tests.length > 0 && (
          <View style={styles.section}>
            <Text variant="label" color="mist" style={styles.sectionLabel}>RESULTS</Text>
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {tests.map((test, idx) => (
                <React.Fragment key={`${test.name}-${idx}`}>
                  {idx > 0 && <View style={styles.divider} />}
                  <TestResultRow test={test} onLongPress={() => handleLongPress(test)} />
                </React.Fragment>
              ))}
            </Card>
          </View>
        )}

        {tests.length === 0 && (
          <Text variant="bodySmall" color="mist" style={{ textAlign: 'center' }}>
            No parsed test results for this report.
          </Text>
        )}
      </ScrollView>

      {/* Convert action sheet */}
      <ActionSheet
        visible={showActionSheet}
        title={selectedTest?.name ?? ''}
        subtitle={selectedTest ? `${selectedTest.value} ${selectedTest.unit}` : undefined}
        actions={actionSheetActions}
        onAction={(actionId) => {
          if (actionId === 'choose_type') {
            setShowActionSheet(false);
            setShowTypeSheet(true);
          } else if (actionId.startsWith('convert:')) {
            const type = actionId.slice('convert:'.length);
            void handleConvert(type);
          }
        }}
        onClose={() => setShowActionSheet(false)}
      />

      {/* Type picker sheet */}
      <ActionSheet
        visible={showTypeSheet}
        title="Choose measurement type"
        actions={typeSheetActions}
        onAction={(actionId) => {
          if (actionId.startsWith('type:')) {
            const type = actionId.slice('type:'.length);
            void handleConvert(type);
          }
        }}
        onClose={() => setShowTypeSheet(false)}
      />
    </SafeAreaView>
  );
}

// ── Test result row ───────────────────────────────────────────────────────────

function TestResultRow({ test, onLongPress }: { test: ParsedTest; onLongPress: () => void }) {
  const isAbnormal = test.flag !== 'normal';

  return (
    <Pressable
      onLongPress={onLongPress}
      delayLongPress={400}
      style={({ pressed }) => [styles.testRow, pressed && { backgroundColor: tokens.divider }]}
    >
      <View style={{ flex: 1 }}>
        <Text
          variant="body"
          color="ink"
          style={isAbnormal ? { fontFamily: 'GeistSans-Medium' } : undefined}
        >
          {test.name}
        </Text>
        {(test.ref_low != null || test.ref_high != null) && (
          <Text variant="caption" color="mist">
            ref: {test.ref_low ?? '–'} – {test.ref_high ?? '–'} {test.unit}
          </Text>
        )}
      </View>
      <View style={styles.testRight}>
        <Text
          variant="body"
          style={{
            fontFamily: 'GeistMono-Regular',
            color: isAbnormal ? tokens.warning : tokens.ink,
          }}
        >
          {test.value}
        </Text>
        {test.unit ? (
          <Text variant="caption" color="mist" style={{ marginLeft: tokens.s4 }}>
            {test.unit}
          </Text>
        ) : null}
        {test.flag !== 'normal' && (
          <View style={{ marginLeft: tokens.s8 }}>
            <StatusBadge label={test.flag} variant={FLAG_TO_BADGE[test.flag]} />
          </View>
        )}
      </View>
    </Pressable>
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
  titleBlock: { gap: tokens.s4 },
  viewOriginalBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.s4,
    marginTop: tokens.s4,
    alignSelf: 'flex-start',
  },
  summaryCard: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap' },
  summaryRow: { flexDirection: 'row', alignItems: 'baseline' },
  summaryDivider: {
    width: 1,
    height: 20,
    backgroundColor: tokens.hairline,
    marginHorizontal: tokens.s12,
  },
  section: { gap: tokens.s8 },
  sectionLabel: { textTransform: 'uppercase', letterSpacing: 1 },
  divider: { height: 1, backgroundColor: tokens.hairline },
  testRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: tokens.s16,
    paddingVertical: tokens.s12,
    gap: tokens.s12,
  },
  testRight: {
    flexDirection: 'row',
    alignItems: 'center',
    flexShrink: 0,
  },
  loadingState: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s24,
  },
  sk: {
    height: 16,
    borderRadius: tokens.radii.card,
    backgroundColor: tokens.hairline,
  },
});
