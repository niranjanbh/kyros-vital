import { tokens } from '../theme/tokens';

export const CATEGORY_LABELS: Record<string, string> = {
  medication:  'Medication',
  water:       'Water',
  meal:        'Meals',
  workout:     'Workout',
  vital_check: 'Vitals',
  custom:      'Custom',
};

export const FILTER_CHIPS = [
  { key: 'all',        label: 'All' },
  { key: 'medication', label: 'Medication' },
  { key: 'water',      label: 'Water' },
  { key: 'meal',       label: 'Meals' },
  { key: 'workout',    label: 'Workout' },
  { key: 'vital_check',label: 'Vitals' },
  { key: 'custom',     label: 'Custom' },
] as const;

export function getCategoryColor(category: string): string {
  return tokens.categoryColors[category as keyof typeof tokens.categoryColors]
    ?? tokens.mist;
}

export function getItemSubtitle(item: {
  category: string;
  metadata: Record<string, any>;
  reminders?: any[];
}): string {
  const meta = item.metadata ?? {};
  switch (item.category) {
    case 'medication': {
      const reminderTimes = item.reminders?.[0]?.schedule?.times?.length;
      const rxText = reminderTimes ? `${reminderTimes}× daily` : '';
      return [meta.drug_name, meta.dosage, rxText].filter(Boolean).join(' · ');
    }
    case 'water':
      return meta.daily_target_ml ? `${meta.daily_target_ml} ml daily` : '';
    case 'workout':
      return [
        meta.workout_type,
        meta.duration_minutes ? `${meta.duration_minutes} min` : '',
      ]
        .filter(Boolean)
        .join(' · ');
    case 'meal':
      return meta.meal_name ?? '';
    case 'vital_check':
      return item.reminders?.[0]?.schedule ? 'Scheduled' : 'On demand';
    case 'custom':
      return meta.title ?? '';
    default:
      return '';
  }
}

export const ACTION_DISPLAY: Record<string, { label: string; color: 'positive' | 'warning' | 'slate' }> = {
  taken:        { label: 'Taken',        color: 'positive' },
  skipped:      { label: 'Skipped',      color: 'warning' },
  snoozed:      { label: 'Snoozed',      color: 'slate' },
  logged_value: { label: 'Logged',       color: 'positive' },
  acknowledged: { label: 'Acknowledged', color: 'slate' },
};
