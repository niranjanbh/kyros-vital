import { Text as RNText, TextStyle } from 'react-native';
import { typography, TypographyVariant } from '../theme/typography';
import { tokens, TokenColor } from '../theme/tokens';

interface TextProps {
  variant?: TypographyVariant;
  color?: TokenColor;
  children: React.ReactNode;
  style?: TextStyle;
  numberOfLines?: number;
}

export function Text({ variant = 'body', color = 'ink', children, style, numberOfLines }: TextProps) {
  return (
    <RNText
      style={[typography[variant], { color: tokens[color] }, style]}
      numberOfLines={numberOfLines}
    >
      {children}
    </RNText>
  );
}
