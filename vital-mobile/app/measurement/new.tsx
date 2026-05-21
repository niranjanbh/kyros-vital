import { DateInput } from '../../src/components/DateInput';
import React, { useState, useEffect } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { format } from 'date-fns';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Input } from '../../src/components/Input';
import { Button } from '../../src/components/Button';
import { FormField } from '../../src/components/FormField';
import { SegmentedControl } from '../../src/components/SegmentedControl';
import { MEASUREMENT_META, ALL_MEASUREMENT_TYPES } from '../../src/charts/utils';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { getApiClient } from '../../src/api/client';

const TYPE_OPTIONS = ALL_MEASUREMENT_TYPES.map((t) => ({
  value: t,
  label: MEASUREMENT_META[t]?.label ?? t,
}));

// BP is a special compound type that creates two rows
const BP_TYPES = new Set(['bp_systolic', 'bp_diastolic']);
const IS_BP_COMPOUND = (type: string) => type === 'bp';

export default function NewMeasurementScreen() {
  const params = useLocalSearchParams<{ type?: string }>();

  const [type, setType] = useState(params.type ?? 'weight');
  const [isBP, setIsBP] = useState(type === 'bp');
  const [value, setValue] = useState('');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [unit, setUnit] = useState(MEASUREMENT_META[type]?.defaultUnit ?? 'kg');
  const [note, setNote] = useState('');
  const [measuredAt, setMeasuredAt] = useState(new Date());

  const qc = useQueryClient();

  // Update unit when type changes
  useEffect(() => {
    const meta = MEASUREMENT_META[type];
    if (meta) setUnit(meta.defaultUnit);
    setIsBP(type === 'bp');
  }, [type]);

  const createMeasurement = useMutation({
    mutationFn: async (payload: {
      type: string;
      value: string;
      unit: string;
      measured_at: string;
      note?: string;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.POST('/v1/wellness/measurements/', {
        body: payload as any,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['measurements'] });
      qc.invalidateQueries({ queryKey: ['measurements-recent-30d'] });
    },
  });

  const handleSubmit = async () => {
    const isoTime = measuredAt.toISOString();
    const noteVal = note.trim() || undefined;

    try {
      if (isBP) {
        // BP creates two rows linked by measured_at
        if (!systolic || !diastolic) {
          Alert.alert('Validation', 'Enter both systolic and diastolic values.');
          return;
        }
        await createMeasurement.mutateAsync({
          type: 'bp_systolic',
          value: systolic,
          unit: 'mmHg',
          measured_at: isoTime,
          note: noteVal,
        });
        await createMeasurement.mutateAsync({
          type: 'bp_diastolic',
          value: diastolic,
          unit: 'mmHg',
          measured_at: isoTime,
          note: noteVal,
        });
      } else {
        if (!value) {
          Alert.alert('Validation', 'Enter a value.');
          return;
        }
        await createMeasurement.mutateAsync({
          type,
          value,
          unit,
          measured_at: isoTime,
          note: noteVal,
        });
      }
      router.back();
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Something went wrong.');
    }
  };

  const displayType = isBP ? 'Blood Pressure' : MEASUREMENT_META[type]?.label ?? type;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        {/* Header */}
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
          </Pressable>
          <Text variant="h1" color="ink" style={styles.title}>
            New Measurement
          </Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          {/* Type selector — scrollable segmented row */}
          <FormField label="Type">
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.typeChips}
            >
              {/* BP compound option */}
              <Pressable
                style={[styles.typeChip, isBP && styles.typeChipActive]}
                onPress={() => { setType('bp_systolic'); setIsBP(true); }}
              >
                <Text
                  variant="bodySmall"
                  color={isBP ? 'ink' : 'slate'}
                  style={isBP ? { fontFamily: 'GeistSans-Medium' } : undefined}
                >
                  BP
                </Text>
              </Pressable>
              {ALL_MEASUREMENT_TYPES.filter(t => !BP_TYPES.has(t)).map((t) => (
                <Pressable
                  key={t}
                  style={[styles.typeChip, !isBP && type === t && styles.typeChipActive]}
                  onPress={() => { setType(t); setIsBP(false); }}
                >
                  <Text
                    variant="bodySmall"
                    color={!isBP && type === t ? 'ink' : 'slate'}
                    style={!isBP && type === t ? { fontFamily: 'GeistSans-Medium' } : undefined}
                  >
                    {MEASUREMENT_META[t]?.label}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
          </FormField>

          {/* Value input */}
          {isBP ? (
            <>
              <FormField label="Systolic (mmHg)">
                <Input
                  value={systolic}
                  onChangeText={setSystolic}
                  keyboardType="decimal-pad"
                  placeholder="e.g. 118"
                />
              </FormField>
              <FormField label="Diastolic (mmHg)">
                <Input
                  value={diastolic}
                  onChangeText={setDiastolic}
                  keyboardType="decimal-pad"
                  placeholder="e.g. 76"
                />
              </FormField>
            </>
          ) : (
            <FormField label={`Value`}>
              <View style={styles.valueRow}>
                <Input
                  value={value}
                  onChangeText={setValue}
                  keyboardType="decimal-pad"
                  placeholder="0"
                  style={styles.valueInput}
                />
                <Input
                  value={unit}
                  onChangeText={setUnit}
                  placeholder="unit"
                  style={styles.unitInput}
                />
              </View>
            </FormField>
          )}

          {/* Date/time */}
          <FormField label="Measured At">
            <DateInput
              mode="datetime"
              value={measuredAt}
              onChange={setMeasuredAt}
              maximumDate={new Date()}
            />
          </FormField>

          {/* Note */}
          <FormField label="Note (optional)">
            <Input
              value={note}
              onChangeText={setNote}
              placeholder="e.g. After fasting"
              multiline
              style={{ minHeight: 64, textAlignVertical: 'top' }}
            />
          </FormField>

          <Button
            onPress={handleSubmit}
            variant="primary"
            style={styles.saveBtn}
            disabled={createMeasurement.isPending}
          >
            {createMeasurement.isPending ? 'Saving…' : `Save ${displayType}`}
          </Button>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

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
  content: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s16,
    paddingBottom: tokens.s48,
    gap: tokens.s24,
  },
  typeChips: {
    flexDirection: 'row',
    gap: tokens.s8,
    paddingBottom: tokens.s4,
  },
  typeChip: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: 6,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  typeChipActive: {
    borderColor: tokens.ink,
    backgroundColor: tokens.divider,
  },
  valueRow: {
    flexDirection: 'row',
    gap: tokens.s8,
  },
  valueInput: { flex: 1 },
  unitInput: { width: 80, textAlign: 'center' },
  dateBtn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
  },
  saveBtn: { marginTop: tokens.s8 },
});
