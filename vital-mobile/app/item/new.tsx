import { Pressable, SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { ArrowLeft, Pill, Droplet, Dumbbell, Utensils, Activity, Tag } from 'lucide-react-native';

import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { getCategoryColor } from '../../src/utils/itemHelpers';

const CATEGORIES = [
  {
    id: 'medication',
    name: 'Medication',
    description: 'Track pills, syrups, and injections with dosage reminders',
    icon: Pill,
  },
  {
    id: 'water',
    name: 'Water',
    description: 'Set a daily hydration target with interval reminders',
    icon: Droplet,
  },
  {
    id: 'workout',
    name: 'Workout',
    description: 'Log exercise sessions and get reminded to move',
    icon: Dumbbell,
  },
  {
    id: 'meal',
    name: 'Meal',
    description: 'Track meal times and nutrition habits',
    icon: Utensils,
  },
  {
    id: 'vital_check',
    name: 'Vitals',
    description: 'Blood pressure, glucose, weight, and other measurements',
    icon: Activity,
  },
  {
    id: 'custom',
    name: 'Custom',
    description: 'Build any tracking habit with a fully custom schedule',
    icon: Tag,
  },
] as const;

export default function CategoryPickerScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <ArrowLeft size={22} color={tokens.ink} strokeWidth={1.5} />
        </Pressable>
        <Text variant="h1" color="ink" style={styles.title}>Add Item</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text variant="body" color="slate" style={styles.subtitle}>
          What would you like to track?
        </Text>

        {CATEGORIES.map((cat) => {
          const accentColor = getCategoryColor(cat.id);
          const Icon = cat.icon;
          return (
            <Pressable
              key={cat.id}
              style={({ pressed }) => [styles.card, pressed && { opacity: 0.75 }]}
              onPress={() => router.push(`/item/new/${cat.id === 'vital_check' ? 'vital_check' : cat.id}` as any)}
            >
              <View style={[styles.iconBadge, { backgroundColor: `${accentColor}18` }]}>
                <Icon size={22} color={accentColor} strokeWidth={1.5} />
              </View>
              <View style={styles.cardContent}>
                <Text variant="body" color="ink" style={{ fontFamily: 'GeistSans-Medium' }}>
                  {cat.name}
                </Text>
                <Text variant="bodySmall" color="slate">{cat.description}</Text>
              </View>
            </Pressable>
          );
        })}
      </ScrollView>
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
    gap: tokens.s12,
  },
  subtitle: { marginBottom: tokens.s8 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    padding: tokens.s16,
    gap: tokens.s16,
  },
  iconBadge: {
    width: 44,
    height: 44,
    borderRadius: tokens.radii.card,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardContent: { flex: 1, gap: tokens.s4 },
});
