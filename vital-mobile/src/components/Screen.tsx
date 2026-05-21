import { SafeAreaView, ScrollView, StyleSheet, ViewStyle } from 'react-native';
import { tokens } from '../theme/tokens';

interface ScreenProps {
  children: React.ReactNode;
  scrollable?: boolean;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
}

export function Screen({ children, scrollable = true, style, contentStyle }: ScreenProps) {
  if (scrollable) {
    return (
      <SafeAreaView style={[styles.safe, style]}>
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[styles.content, contentStyle]}
          showsVerticalScrollIndicator={false}
        >
          {children}
        </ScrollView>
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView style={[styles.safe, style]}>
      {children}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: tokens.bone,
  },
  scroll: {
    flex: 1,
  },
  content: {
    padding: tokens.s16,
    paddingBottom: tokens.s48,
  },
});
