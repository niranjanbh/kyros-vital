import React from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useForm, useController } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft } from 'lucide-react-native';
import { format } from 'date-fns';

import { tokens } from '../../../src/theme/tokens';
import { Text } from '../../../src/components/Text';
import { Input } from '../../../src/components/Input';
import { Button } from '../../../src/components/Button';
import { FormField } from '../../../src/components/FormField';
import { TimePicker } from '../../../src/components/TimePicker';
import { DayOfWeekPicker } from '../../../src/components/DayOfWeekPicker';
import { useCreateTrackedItem, useCreateReminder } from '../../../src/api/queries';
import { ALL_DAYS_ARRAY } from '../../../src/utils/schedule';

const schema = z.object({
  daily_target_ml: z.number().min(100, 'Enter at least 100 ml').max(10000),
  reminder_interval_minutes: z.number().min(15, 'Minimum 15 min').max(480),
  window_start: z.string(),
  window_end: z.string(),
  days_of_week: z.array(z.string()).min(1, 'Select at least one day'),
});
type F = z.infer<typeof schema>;

function FInput({ name, control }: any) {
  const { field, fieldState } = useController({ name, control });
  return (
    <Input
      value={String(field.value ?? '')}
      onChangeText={(t) => { const n = Number(t); if (!isNaN(n)) field.onChange(n); }}
      keyboardType="numeric"
      error={fieldState.error?.message}
    />
  );
}
function FTime({ name, control }: any) {
  const { field } = useController({ name, control });
  return <TimePicker value={field.value ?? '08:00'} onChange={field.onChange} />;
}
function FDays({ name, control }: any) {
  const { field } = useController({ name, control });
  return <DayOfWeekPicker selected={field.value ?? []} onChange={field.onChange} />;
}

export default function WaterForm() {
  const createItem = useCreateTrackedItem();
  const createReminder = useCreateReminder();

  const { control, handleSubmit, formState: { isSubmitting } } = useForm<F>({
    resolver: zodResolver(schema),
    defaultValues: {
      daily_target_ml: 2500,
      reminder_interval_minutes: 120,
      window_start: '08:00',
      window_end: '22:00',
      days_of_week: [...ALL_DAYS_ARRAY],
    },
  });

  const onSubmit = async (v: F) => {
    try {
      const item = await createItem.mutateAsync({
        category: 'water',
        name: 'Daily Hydration',
        metadata: { daily_target_ml: v.daily_target_ml, glass_size_ml: 250 } as any,
        start_date: format(new Date(), 'yyyy-MM-dd'),
      });
      await createReminder.mutateAsync({
        itemId: (item as any).id,
        schedule: {
          type: 'interval',
          interval_minutes: v.reminder_interval_minutes,
          active_window: { start: v.window_start, end: v.window_end },
          days_of_week: v.days_of_week,
          start_date: format(new Date(), 'yyyy-MM-dd'),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        } as any,
        message_template: 'Drink {glass_size_ml} ml of water',
      });
      router.replace('/(tabs)/library');
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? 'Something went wrong.');
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
          </Pressable>
          <Text variant="h1" color="ink" style={styles.title}>Add Water Goal</Text>
          <View style={{ width: 22 }} />
        </View>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <FormField label="Daily Target (ml)" hint="e.g. 2500 ml = 10 glasses of 250 ml">
            <FInput name="daily_target_ml" control={control} />
          </FormField>
          <FormField label="Remind Every (minutes)" hint="120 = every 2 hours">
            <FInput name="reminder_interval_minutes" control={control} />
          </FormField>
          <FormField label="Active Window Start">
            <FTime name="window_start" control={control} />
          </FormField>
          <FormField label="Active Window End">
            <FTime name="window_end" control={control} />
          </FormField>
          <FormField label="Active Days">
            <FDays name="days_of_week" control={control} />
          </FormField>
          <Button onPress={handleSubmit(onSubmit)} variant="primary" style={styles.btn} disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Add Water Goal'}
          </Button>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: tokens.s20, paddingTop: tokens.s16, paddingBottom: tokens.s8,
  },
  title: { flex: 1, textAlign: 'center' },
  content: { paddingHorizontal: tokens.s20, paddingTop: tokens.s16, paddingBottom: tokens.s48, gap: tokens.s24 },
  btn: { marginTop: tokens.s8 },
});
