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
  name: z.string().min(1, 'Name is required'),
  time: z.string(),
  days_of_week: z.array(z.string()).min(1),
});
type F = z.infer<typeof schema>;

function FText({ name, control, placeholder }: any) {
  const { field, fieldState } = useController({ name, control });
  return <Input value={field.value ?? ''} onChangeText={field.onChange} placeholder={placeholder} error={fieldState.error?.message} />;
}
function FTime({ name, control }: any) {
  const { field } = useController({ name, control });
  return <TimePicker value={field.value ?? '08:00'} onChange={field.onChange} />;
}
function FDays({ name, control }: any) {
  const { field } = useController({ name, control });
  return <DayOfWeekPicker selected={field.value ?? []} onChange={field.onChange} />;
}

export default function VitalCheckForm() {
  const createItem = useCreateTrackedItem();
  const createReminder = useCreateReminder();

  const { control, handleSubmit, formState: { isSubmitting } } = useForm<F>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', time: '08:00', days_of_week: [...ALL_DAYS_ARRAY] },
  });

  const onSubmit = async (v: F) => {
    try {
      const item = await createItem.mutateAsync({
        category: 'vital_check',
        name: v.name,
        metadata: {} as any,
        start_date: format(new Date(), 'yyyy-MM-dd'),
      });
      await createReminder.mutateAsync({
        itemId: (item as any).id,
        schedule: {
          type: 'recurring',
          times: [v.time],
          days_of_week: v.days_of_week,
          start_date: format(new Date(), 'yyyy-MM-dd'),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        } as any,
        message_template: `Time to check your ${v.name}`,
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
          <Text variant="h1" color="ink" style={styles.title}>Add Vital Check</Text>
          <View style={{ width: 22 }} />
        </View>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <FormField label="What to Check" required>
            <FText name="name" control={control} placeholder="e.g. Blood Pressure" />
          </FormField>
          <FormField label="Reminder Time">
            <FTime name="time" control={control} />
          </FormField>
          <FormField label="Days">
            <FDays name="days_of_week" control={control} />
          </FormField>
          <Button onPress={handleSubmit(onSubmit)} variant="primary" style={styles.btn} disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Add Vital Check'}
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
