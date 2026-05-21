import React, { useRef, useState } from 'react';
import {
  Dimensions,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { storage } from '../src/utils/storage';
import { tokens } from '../src/theme/tokens';
import { Text } from '../src/components/Text';
import { Button } from '../src/components/Button';
import { Input } from '../src/components/Input';
import { requestPermissions } from '../src/notifications/permissions';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const GENDERS = ['Male', 'Female', 'Other', 'Prefer not to say'] as const;

export default function OnboardingScreen() {
  const scrollRef = useRef<ScrollView>(null);
  const [currentPage, setCurrentPage] = useState(0);

  // Profile fields (page 2)
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const page = Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH);
    setCurrentPage(page);
  };

  const handleContinue = async () => {
    if (currentPage < 2) {
      const nextPage = currentPage + 1;
      scrollRef.current?.scrollTo({ x: nextPage * SCREEN_WIDTH, animated: true });
      setCurrentPage(nextPage);
    } else {
      // Save profile if provided
      if (name.trim()) await storage.setItem('vital_profile_name', name.trim());
      if (age.trim()) await storage.setItem('vital_profile_age', age.trim());
      if (gender) await storage.setItem('vital_profile_gender', gender);

      try { await requestPermissions(); } catch { /* optional */ }
      await storage.setItem('vital_onboarded', '1');
      router.replace('/(tabs)/library');
    }
  };

  const isLastPage = currentPage === 2;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        scrollEventThrottle={16}
        onScroll={handleScroll}
        style={styles.pager}
        scrollEnabled={false}
      >
        {/* Page 1 */}
        <View style={[styles.page, { width: SCREEN_WIDTH }]}>
          <View style={styles.pageContent}>
            <Text variant="displayL" color="ink">Your wellness,{'\n'}in one place.</Text>
            <Text variant="body" color="slate" style={styles.pageBody}>
              Track medications, hydration, workouts, and more — no account needed.
            </Text>
          </View>
        </View>

        {/* Page 2 */}
        <View style={[styles.page, { width: SCREEN_WIDTH }]}>
          <View style={styles.pageContent}>
            <Text variant="displayL" color="ink">Reminders that respect your day.</Text>
            <Text variant="body" color="slate" style={styles.pageBody}>
              Everything stays local and private on your device. No cloud sync, no account required.
            </Text>
          </View>
        </View>

        {/* Page 3 — profile */}
        <View style={[styles.page, { width: SCREEN_WIDTH }]}>
          <View style={styles.pageContent}>
            <Text variant="displayL" color="ink">Tell us a little about you.</Text>
            <Text variant="body" color="slate" style={styles.pageBody}>
              Optional — used to personalise reminders. Stays on device only.
            </Text>

            <View style={styles.fields}>
              <View>
                <Text variant="label" color="mist" style={styles.fieldLabel}>YOUR NAME</Text>
                <Input
                  value={name}
                  onChangeText={setName}
                  placeholder="e.g. Alex"
                  autoCapitalize="words"
                />
              </View>

              <View>
                <Text variant="label" color="mist" style={styles.fieldLabel}>AGE</Text>
                <Input
                  value={age}
                  onChangeText={setAge}
                  placeholder="e.g. 35"
                  keyboardType="number-pad"
                />
              </View>

              <View>
                <Text variant="label" color="mist" style={styles.fieldLabel}>GENDER</Text>
                <View style={styles.genderChips}>
                  {GENDERS.map((g) => (
                    <Pressable
                      key={g}
                      style={[styles.genderChip, gender === g && styles.genderChipActive]}
                      onPress={() => setGender(gender === g ? '' : g)}
                    >
                      <Text
                        variant="bodySmall"
                        color={gender === g ? 'ink' : 'slate'}
                        style={gender === g ? { fontFamily: 'GeistSans-Medium' } : undefined}
                      >
                        {g}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Progress dots */}
      <View style={styles.dots}>
        {[0, 1, 2].map((i) => (
          <View
            key={i}
            style={[styles.dot, i === currentPage ? styles.dotActive : styles.dotInactive]}
          />
        ))}
      </View>

      <View style={styles.buttonContainer}>
        <Button variant="primary" onPress={handleContinue}>
          {isLastPage ? 'Get started' : 'Continue'}
        </Button>
        {isLastPage && (
          <Pressable onPress={handleContinue} style={styles.skipBtn}>
            <Text variant="bodySmall" color="mist">Skip for now</Text>
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  pager: { flex: 1 },
  page: { flex: 1, justifyContent: 'center', paddingHorizontal: tokens.s32 },
  pageContent: { gap: tokens.s24 },
  pageBody: { lineHeight: 24 },
  fields: { gap: tokens.s16 },
  fieldLabel: { textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: tokens.s4 },
  genderChips: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.s8 },
  genderChip: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    borderRadius: tokens.radii.button,
    paddingVertical: 6,
    paddingHorizontal: tokens.s12,
    backgroundColor: tokens.paper,
  },
  genderChipActive: { borderColor: tokens.ink, backgroundColor: tokens.divider },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: tokens.s8,
    paddingVertical: tokens.s16,
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  dotActive: { backgroundColor: tokens.ink },
  dotInactive: { backgroundColor: tokens.hairline },
  buttonContainer: {
    paddingHorizontal: tokens.s32,
    paddingBottom: tokens.s32,
    gap: tokens.s12,
    alignItems: 'center',
  },
  skipBtn: { paddingVertical: tokens.s8 },
});
