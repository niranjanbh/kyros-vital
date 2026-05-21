import type { TextStyle } from 'react-native';

export const typography: Record<string, TextStyle> = {
  displayXL: {
    fontFamily: 'Fraunces-Variable',
    fontSize: 64,
    lineHeight: 68,
    letterSpacing: -1.5,
  },
  displayL: {
    fontFamily: 'Fraunces-Variable',
    fontSize: 48,
    lineHeight: 52,
    letterSpacing: -1,
  },
  displayM: {
    fontFamily: 'Fraunces-Variable',
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: -0.5,
  },
  h1: {
    fontFamily: 'GeistSans-SemiBold',
    fontSize: 24,
    lineHeight: 30,
    letterSpacing: -0.3,
  },
  h2: {
    fontFamily: 'GeistSans-SemiBold',
    fontSize: 18,
    lineHeight: 24,
    letterSpacing: -0.2,
  },
  body: {
    fontFamily: 'GeistSans-Regular',
    fontSize: 15,
    lineHeight: 22,
    letterSpacing: 0,
  },
  bodySmall: {
    fontFamily: 'GeistSans-Regular',
    fontSize: 13,
    lineHeight: 18,
    letterSpacing: 0,
  },
  caption: {
    fontFamily: 'GeistSans-Regular',
    fontSize: 11,
    lineHeight: 15,
    letterSpacing: 0.3,
  },
  label: {
    fontFamily: 'GeistSans-Medium',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.8,
  },
  mono: {
    fontFamily: 'GeistMono-Regular',
    fontSize: 13,
    lineHeight: 18,
    letterSpacing: 0,
  },
};

export type TypographyVariant = keyof typeof typography;
