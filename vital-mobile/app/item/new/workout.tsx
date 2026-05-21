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
  workout_type: z.string().min(1, 'Workout type is required'),
  duration_minutes: z.number().min(1, 'Duration required').max(480),
  time_of_day: z.string(),
  days_of_week: z.array(z.string()).min(1, 'Select at least one day'),
  location: z.string().optional(),
});
type F = z.infer<typeof schema>;

function FText({ name, control, placeholder }: any) {
  const { field, fieldState } = useController({ name, control });
  return <Input value={field.value ?? ''} onChangeText={field.onChange} placeholder={placeholder} error={fieldState.error?.message} />;
}
function FNum({ name, control }: any) {
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
  return <TimePicker value={field.value ?? '07:00'} onChange={field.onChange} />;
}
function FDays({ name, control }: any) {
  const { field } = useController({ name, control });
  return <DayOfWeekPicker selected={field.value ?? []} onChange={field.onChange} />;
}

export default function WorkoutForm() {
  const createItem = useCreateTrackedItem();
  const createReminder = useCreateReminder();

  const { control, handleSubmit, watch, formState: { isSubmitting } } = useForm<F>({
    resolver: zodResolver(schema),
    defaultValues: {
      workout_type: '',
      duration_minutes: 45,
      time_of_day: '07:00',
      days_of_week: ['mon', 'wed', 'fri'],
      location: '',
    },
  });

  const onSubmit = async (v: F) => {
    try {
      const item = await createItem.mutateAsync({
        category: 'workout',
        name: v.workout_type,
        metadata: {
          workout_type: v.workout_type,
          duration_minutes: v.duration_minutes,
          location: v.location ?? null,
        } as any,
        start_date: format(new Date(), 'yyyy-MM-dd'),
      });
      await createReminder.mutateAsync({
        itemId: (item as any).id,
        schedule: {
          type: 'recurring',
          times: [v.time_of_day],
          days_of_week: v.days_of_week,
          start_date: format(new Date(), 'yyyy-MM-dd'),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        } as any,
        message_template: '{workout_type} workout · {duration_minutes} min',
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
          <Pressable onPress={() => router.back()} hitSlop={12}><ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} /></Pressable>
          <Text variant="h1" color="ink" style={styles.title}>Add Workout</Text>
          <View style={{ width: 22 }} />
        </View>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <FormField label="Workout Type" required>
            <FText name="workout_type" control={control} placeholder="e.g. Strength Training" />
          </FormField>
          <FormField label="Duration (minutes)">
            <FNum name="duration_minutes" control={control} />
          </FormField>
          <FormField label="Time of Day">
            <FTime name="time_of_day" control={control} />
          </FormField>
          <FormField label="Days">
            <FDays name="days_of_week" control={control} />
          </FormField>
          <FormField label="Location (optional)">
            <FText name="location" control={control} placeholder="e.g. Gym, Home, Park" />
          </FormField>
          <Button onPress={handleSubmit(onSubmit)} variant="primary" style={styles.btn} disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Add Workout'}
          </Button>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: tokens.s20, paddingTop: tokens.s16, paddingBottom: tokens.s8 },
  title: { flex: 1, textAlign: 'center' },
  content: { paddingHorizontal: tokens.s20, paddingTop: tokens.s16, paddingBottom: tokens.s48, gap: tokens.s24 },
  btn: { marginTop: tokens.s8 },
});
