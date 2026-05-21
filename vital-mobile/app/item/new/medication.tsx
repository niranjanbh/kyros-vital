import { DateInput } from '../../../src/components/DateInput';
import React, { useEffect } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useForm, useController, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';
import { ArrowLeft, Plus, Trash2 } from 'lucide-react-native';

import { tokens } from '../../../src/theme/tokens';
import { Text } from '../../../src/components/Text';
import { Input } from '../../../src/components/Input';
import { Button } from '../../../src/components/Button';
import { FormField } from '../../../src/components/FormField';
import { TimePicker } from '../../../src/components/TimePicker';
import { DayOfWeekPicker } from '../../../src/components/DayOfWeekPicker';
import { NumberStepper } from '../../../src/components/NumberStepper';
import { SegmentedControl } from '../../../src/components/SegmentedControl';
import { Toggle } from '../../../src/components/Toggle';
import { useCreateTrackedItem, useCreateReminder, usePatchTrackedItem, useTrackedItem } from '../../../src/api/queries';
import { defaultTimesForDoses, ALL_DAYS_ARRAY } from '../../../src/utils/schedule';

const FORM_TYPES = [
  { value: 'tablet', label: 'Tablet' },
  { value: 'capsule', label: 'Capsule' },
  { value: 'syrup', label: 'Syrup' },
  { value: 'injection', label: 'Injection' },
  { value: 'other', label: 'Other' },
];

const schema = z.object({
  drug_name: z.string().min(1, 'Drug name is required'),
  dosage: z.string().min(1, 'Dosage is required'),
  form: z.enum(['tablet', 'capsule', 'syrup', 'injection', 'other']),
  times_per_day: z.number().min(1).max(6),
  specific_times: z.array(z.string()).min(1),
  days_of_week: z.array(z.string()).min(1, 'Select at least one day'),
  with_food: z.boolean(),
  start_date: z.string(),
  has_end_date: z.boolean(),
  end_date: z.string().optional(),
  instructions: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function MedicationForm() {
  const { itemId } = useLocalSearchParams<{ itemId?: string }>();
  const isEdit = !!itemId;

  const { data: existing } = useTrackedItem(itemId ?? '');
  const createItem = useCreateTrackedItem();
  const patchItem = usePatchTrackedItem();
  const createReminder = useCreateReminder();

  const { control, handleSubmit, watch, setValue, getValues,formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      drug_name: '',
      dosage: '',
      form: 'tablet',
      times_per_day: 2,
      specific_times: ['08:00', '20:00'],
      days_of_week: [...ALL_DAYS_ARRAY],
      with_food: false,
      start_date: format(new Date(), 'yyyy-MM-dd'),
      has_end_date: false,
      end_date: undefined,
      instructions: '',
    },
  });
  // Prefill form when editing
  useEffect(() => {
    if (isEdit && existing) {
      const meta = existing.metadata as Record<string, any>;
      const reminder = (existing.reminders as any[])?.[0];
      const sched = reminder?.schedule;
      setValue('drug_name', meta.drug_name ?? '');
      setValue('dosage', meta.dosage ?? '');
      setValue('form', meta.form ?? 'tablet');
      setValue('with_food', meta.with_food ?? false);
      setValue('instructions', meta.instructions ?? '');
      setValue('start_date', existing.start_date ?? format(new Date(), 'yyyy-MM-dd'));
      if (sched?.times) {
        setValue('specific_times', sched.times);
        setValue('times_per_day', sched.times.length);
      }
      if (sched?.days_of_week) setValue('days_of_week', sched.days_of_week);
    }
  }, [isEdit, existing, setValue]);

  const timesPerDay = watch('times_per_day');
  useEffect(() => {
    const currentTimes = getValues('specific_times') || [];
    if (currentTimes.length !== timesPerDay) {
      const defaults = defaultTimesForDoses(timesPerDay);
      const newTimes = Array.from({ length: timesPerDay }, (_, i) => {
        return currentTimes[i] !== undefined ? currentTimes[i] : defaults[i];
      });

      setValue('specific_times', newTimes);
    }
  }, [timesPerDay, setValue, getValues]);

  const onSubmit = async (values: FormValues) => {
    try {
      const metadata = {
        drug_name: values.drug_name,
        dosage: values.dosage,
        form: values.form,
        with_food: values.with_food,
        instructions: values.instructions ?? null,
      };
      const schedule = {
        type: 'recurring' as const,
        times: values.specific_times,
        days_of_week: values.days_of_week,
        start_date: values.start_date,
        end_date: values.has_end_date ? values.end_date : null,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      };
      const name = `${values.drug_name} ${values.dosage}`.trim();

      if (isEdit && itemId) {
        await patchItem.mutateAsync({ id: itemId, name, metadata: metadata as any });
        router.back();
      } else {
        const item = await createItem.mutateAsync({
          category: 'medication',
          name,
          metadata: metadata as any,
          start_date: values.start_date,
          end_date: values.has_end_date ? values.end_date ?? null : null,
        });
        await createReminder.mutateAsync({
          itemId: (item as any).id,
          schedule: schedule as any,
          message_template: 'Take {drug_name} {dosage}',
        });
        router.replace('/(tabs)/library');
      }
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Something went wrong.');
    }
  };

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
            {isEdit ? 'Edit Medication' : 'Add Medication'}
          </Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {/* Drug name */}
          <FormField label="Drug Name" error={errors.drug_name?.message} required>
            <FieldInput name="drug_name" control={control} placeholder="e.g. Metformin" />
          </FormField>

          {/* Dosage */}
          <FormField label="Dosage" error={errors.dosage?.message} required>
            <FieldInput name="dosage" control={control} placeholder="e.g. 500 mg" />
          </FormField>

          {/* Form type */}
          <FormField label="Form">
            <FieldSegmented name="form" control={control} options={FORM_TYPES} scrollable />
          </FormField>

          {/* Times per day */}
          <FormField label="Times Per Day">
            <FieldStepper name="times_per_day" control={control} min={1} max={6} />
          </FormField>

          {/* Specific times */}
          <FormField label="Reminder Times">
            <View style={styles.timesGrid}>
              {Array.from({ length: timesPerDay }, (_, i) => (
                <View key={i} style={styles.timeRow}>
                  <Text variant="caption" color="mist" style={styles.doseLabel}>
                    Dose {i + 1}
                  </Text>
                  <FieldTimePicker
                    name={`specific_times.${i}` as any}
                    index={i}
                    control={control}
                  />
                </View>
              ))}
            </View>
          </FormField>

          {/* Days of week */}
          <FormField label="Days" error={errors.days_of_week?.message}>
            <FieldDayPicker name="days_of_week" control={control} />
          </FormField>

          {/* With food */}
          <FormField label="With Food">
            <FieldToggle name="with_food" control={control} label="Take with food or drink" />
          </FormField>

          {/* Start date */}
          <FormField label="Start Date">
            <FieldDatePicker name="start_date" control={control} />
          </FormField>

          {/* End date toggle */}
          <FormField label="Duration">
            <FieldToggle name="has_end_date" control={control} label="Set an end date" />
            {watch('has_end_date') && (
              <View style={{ marginTop: tokens.s8 }}>
                <FieldDatePicker name="end_date" control={control} />
              </View>
            )}
          </FormField>

          {/* Instructions */}
          <FormField label="Instructions (optional)">
            <FieldInput
              name="instructions"
              control={control}
              placeholder="e.g. Take 30 min before meals"
              multiline
            />
          </FormField>

          <Button
            onPress={handleSubmit(onSubmit)}
            variant="primary"
            style={styles.saveBtn}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Medication'}
          </Button>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ── Field controller helpers ──────────────────────────────────────────────────

function FieldInput({ name, control, placeholder, multiline }: any) {
  const { field } = useController({ name, control });
  return (
    <Input
      value={field.value ?? ''}
      onChangeText={field.onChange}
      placeholder={placeholder}
      multiline={multiline}
      style={multiline ? { minHeight: 72, textAlignVertical: 'top' } : undefined}
    />
  );
}

function FieldSegmented({ name, control, options, scrollable }: any) {
  const { field } = useController({ name, control });
  return <SegmentedControl options={options} value={field.value} onChange={field.onChange} scrollable={scrollable} />;
}

function FieldStepper({ name, control, min, max }: any) {
  const { field } = useController({ name, control });
  return <NumberStepper value={field.value} onChange={field.onChange} min={min} max={max} />;
}

function FieldTimePicker({ name, index, control }: any) {
  const { field } = useController({ name, control });

  const timesArray = Array.isArray(field.value) ? field.value : [];
  const currentTime = timesArray[index] ?? '08:00';

  const handleTimeChange = (newTime: string) => {
    const updatedTimes = [...timesArray];

    updatedTimes[index] = newTime;

    field.onChange(updatedTimes);
  };

  return <TimePicker value={currentTime} onChange={handleTimeChange} />;
}

function FieldDayPicker({ name, control }: any) {
  const { field } = useController({ name, control });
  return <DayOfWeekPicker selected={field.value ?? []} onChange={field.onChange} />;
}

function FieldToggle({ name, control, label }: any) {
  const { field } = useController({ name, control });
  return <Toggle value={!!field.value} onChange={field.onChange} label={label} />;
}

function FieldDatePicker({ name, control }: any) {
  const { field } = useController({ name, control });
  const dateValue = field.value ? new Date(field.value) : new Date();
  return (
    <DateInput
      value={dateValue}
      onChange={(date) => field.onChange(format(date, 'yyyy-MM-dd'))}
      maximumDate={new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)}
    />
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
  timesGrid: { gap: tokens.s8 },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: tokens.s12 },
  doseLabel: { width: 44 },
  dateBtn: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.card,
    padding: tokens.s12,
    backgroundColor: tokens.paper,
  },
  saveBtn: { marginTop: tokens.s8 },
});
