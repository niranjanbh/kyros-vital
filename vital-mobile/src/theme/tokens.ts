export const tokens = {
  // Surfaces & text
  bone:      '#F7F4ED',  // warm background
  paper:     '#FFFFFF',
  ink:       '#1A1A1A',
  slate:     '#5C5C5C',  // secondary text
  mist:      '#8C8C8C',  // tertiary / labels
  hairline:  '#E8E3D8',  // 1px borders
  divider:   '#F0EBE0',  // subtle divider
  tealDeep:  '#2D5F5D',  // primary CTA accent

  // Status
  positive:  '#3F6B4E',  // taken / on-target
  warning:   '#B07A1F',  // pending / past-due
  critical:  '#8B2C1F',  // missed / overdue
  chartLine: '#1A1A1A',

  // Per-category accents — muted, journal-quality
  categoryColors: {
    medication:  '#4A5D7E',  // slate navy — clinical
    water:       '#5B8A8F',  // muted seafoam
    workout:     '#8B5A3C',  // warm clay
    meal:        '#7A6F4D',  // olive ochre
    vital_check: '#6B4E71',  // dusky plum
    custom:      '#6B6F4D',  // sage fallback
  },

  // Spacing (8-pt grid)
  s4:  4,
  s8:  8,
  s12: 12,
  s16: 16,
  s20: 20,
  s24: 24,
  s32: 32,
  s48: 48,

  // Radii
  radii: {
    card:   8,
    button: 10,
  },
} as const;

export type TokenColor = keyof Pick<
  typeof tokens,
  'bone' | 'paper' | 'ink' | 'slate' | 'mist' | 'hairline' | 'tealDeep' | 'positive' | 'warning' | 'critical' | 'chartLine' | 'divider'
>;
