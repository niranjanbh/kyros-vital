import React, { useState } from 'react';
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
import { ScheduleBuilder } from '../../../src/components/schedule/ScheduleBuilder';
import {
  scheduleSchema,
  defaultRecurringSchedule,
} from '../../../src/components/schedule/scheduleSchema';
import { useCreateTrackedItem, useCreateReminder } from '../../../src/api/queries';

const metaSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  message: z.string().min(1, 'Reminder message is required'),
});
type MetaValues = z.infer<typeof metaSchema>;

function FText({ name, control, placeholder, multiline }: any) {
  const { field, fieldState } = useController({ name, control });
  return (
    <Input
      value={field.value ?? ''}
      onChangeText={field.onChange}
      placeholder={placeholder}
      multiline={multiline}
      style={multiline ? { minHeight: 72, textAlignVertical: 'top' } : undefined}
      error={fieldState.error?.message}
    />
  );
}

export default function CustomForm() {
  const createItem = useCreateTrackedItem();
  const createReminder = useCreateReminder();

  const [schedule, setSchedule] = useState<Record<string, unknown>>(
    defaultRecurringSchedule() as Record<string, unknown>
  );
  const [scheduleError, setScheduleError] = useState<string | undefined>();

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<MetaValues>({
    resolver: zodResolver(metaSchema),
    defaultValues: { title: '', message: '' },
  });

  const onSubmit = async (v: MetaValues) => {
    // Validate schedule before submitting
    const result = scheduleSchema.safeParse(schedule);
    if (!result.success) {
      setScheduleError(result.error.issues[0]?.message ?? 'Invalid schedule');
      return;
    }
    setScheduleError(undefined);

    const today = format(new Date(), 'yyyy-MM-dd');
    const finalSchedule = { ...result.data, start_date: today };

    try {
      const item = await createItem.mutateAsync({
        category: 'custom',
        name: v.title,
        metadata: { title: v.title, notes: v.message } as any,
        start_date: today,
      });
      await createReminder.mutateAsync({
        itemId: (item as any).id,
        schedule: finalSchedule as any,
        message_template: v.message,
      });
      router.replace('/(tabs)/library');
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
            Add Custom Item
          </Text>
          <View style={{ width: 22 }} />
        </View>

        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <FormField label="Title" required>
            <FText name="title" control={control} placeholder="e.g. Evening Walk" />
          </FormField>

          <FormField label="Reminder Message" required>
            <FText
              name="message"
              control={control}
              placeholder="e.g. Time for your evening walk"
              multiline
            />
          </FormField>

          <FormField label="Schedule">
            <ScheduleBuilder
              value={schedule}
              onChange={setSchedule}
              error={scheduleError}
            />
          </FormField>

          <Button
            onPress={handleSubmit(onSubmit)}
            variant="primary"
            style={styles.btn}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving…' : 'Add Custom Item'}
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
  btn: { marginTop: tokens.s8 },
});
