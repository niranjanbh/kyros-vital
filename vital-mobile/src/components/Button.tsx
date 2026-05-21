import { Pressable, ViewStyle } from 'react-native';
import { tokens } from '../theme/tokens';
import { Text } from './Text';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  onPress: () => void;
  children: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  style?: ViewStyle;
}

const sizeMap: Record<ButtonSize, { paddingVertical: number; paddingHorizontal: number; fontSize: number }> = {
  sm: { paddingVertical: tokens.s8, paddingHorizontal: tokens.s12, fontSize: 13 },
  md: { paddingVertical: tokens.s12, paddingHorizontal: tokens.s16, fontSize: 15 },
  lg: { paddingVertical: tokens.s16, paddingHorizontal: tokens.s24, fontSize: 16 },
};

export function Button({ onPress, children, variant = 'primary', size = 'md', disabled, style }: ButtonProps) {
  const sizing = sizeMap[size];

  const containerStyle: ViewStyle = {
    paddingVertical: sizing.paddingVertical,
    paddingHorizontal: sizing.paddingHorizontal,
    borderRadius: tokens.radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    ...(variant === 'primary' && { backgroundColor: tokens.tealDeep }),
    ...(variant === 'secondary' && { borderWidth: 1, borderColor: tokens.hairline }),
    ...(variant === 'ghost' && {}),
    ...(disabled && { opacity: 0.4 }),
  };

  const textColor = variant === 'primary' ? 'paper' : variant === 'secondary' ? 'ink' : 'slate';

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [containerStyle, pressed && { opacity: 0.75 }, style]}
    >
      <Text variant="body" color={textColor} style={{ fontSize: sizing.fontSize, fontFamily: 'GeistSans-Medium' }}>
        {children}
      </Text>
    </Pressable>
  );
}
