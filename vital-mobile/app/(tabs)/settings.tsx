import React, { useEffect, useState } from 'react';
import {
  Alert,
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  Share,
  StyleSheet,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { ChevronRight, ExternalLink, Trash2 } from 'lucide-react-native';
import { storage } from '../../src/utils/storage';
import { tokens } from '../../src/theme/tokens';
import { Text } from '../../src/components/Text';
import { Toggle } from '../../src/components/Toggle';
import { usePermissionStatus } from '../../src/hooks/usePermissionStatus';
import { requestPermissions } from '../../src/notifications/permissions';
import { getApiClient } from '../../src/api/client';

const SOUND_KEY = 'vital_notif_sound_enabled';

export default function SettingsScreen() {
  const permStatus = usePermissionStatus();
  const [soundEnabled, setSoundEnabled] = useState(true);
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  useEffect(() => {
    storage.getItem(SOUND_KEY).then((v) => {
      if (v !== null) setSoundEnabled(v === '1');
    });
  }, []);

  const handleSoundToggle = async (v: boolean) => {
    setSoundEnabled(v);
    await SecureStore.setItemAsync(SOUND_KEY, v ? '1' : '0');
  };

  const handleNotifToggle = async () => {
    if (permStatus === 'undetermined') {
      await requestPermissions();
    } else {
      await Linking.openSettings();
    }
  };

  const handleExport = async () => {
    try {
      const client = await getApiClient();

      const [itemsRes, logsRes, measurementsRes, labRes] = await Promise.all([
        client.GET('/v1/wellness/tracked-items/', { params: { query: {} } }),
        client.GET('/v1/wellness/logs/', { params: { query: { limit: 1000 } as any } }),
        client.GET('/v1/wellness/measurements/', { params: { query: {} as any } }),
        client.GET('/v1/wellness/lab-reports/', {}),
      ]);

      const bundle = {
        tracked_items: itemsRes.data ?? [],
        logs: logsRes.data ?? [],
        measurements: measurementsRes.data ?? [],
        lab_reports: labRes.data ?? [],
        exported_at: new Date().toISOString(),
      };

      const json = JSON.stringify(bundle, null, 2);

      await Share.share({
        title: 'Vital Data Export',
        message: json,
      });
    } catch (e: any) {
      Alert.alert('Export failed', e?.message ?? 'Something went wrong.');
    }
  };

  const handleDeleteData = () => {
    Alert.alert(
      'Delete all data',
      'This will permanently erase your device ID and all local preferences. Your data on the server will not be deleted. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            await Promise.all([
              SecureStore.deleteItemAsync('vital_device_id'),
              SecureStore.deleteItemAsync('vital_onboarded'),
              SecureStore.deleteItemAsync(SOUND_KEY),
            ]);
            router.replace('/onboarding');
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text variant="displayM" color="ink" style={styles.heading}>
          Settings
        </Text>

        {/* ACCOUNT section */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            ACCOUNT
          </Text>
          <View style={styles.card}>
            <View style={styles.row}>
              <View style={styles.rowLabel}>
                <Text variant="body" color="ink">Guest mode</Text>
                <Text variant="caption" color="mist">
                  You're using Vital without an account. Your data lives only on this device.
                </Text>
              </View>
            </View>
            <View style={styles.divider} />
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={() =>
                Alert.alert(
                  'Coming in Phase 2',
                  'Account sync will be available in Phase 2 of Vital.'
                )
              }
              accessibilityLabel="Sign in to sync — coming in Phase 2"
              accessibilityRole="button"
            >
              <Text variant="body" color="mist" style={{ flex: 1 }}>
                Sign in to sync
              </Text>
              <ChevronRight size={16} color={tokens.mist} strokeWidth={1.5} />
            </Pressable>
          </View>
        </View>

        {/* Notifications section */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            NOTIFICATIONS
          </Text>
          <View style={styles.card}>
            {/* Allow notifications */}
            <View style={styles.row}>
              <View style={styles.rowLabel}>
                <Text variant="body" color="ink">Allow notifications</Text>
                <Text variant="caption" color="mist">
                  {permStatus === 'granted'
                    ? 'Enabled — manage in Settings'
                    : permStatus === 'denied'
                    ? 'Denied — tap to open Settings'
                    : 'Tap to request permission'}
                </Text>
              </View>
              {permStatus === 'granted' ? (
                <Pressable onPress={handleNotifToggle} hitSlop={12}>
                  <ExternalLink size={18} color={tokens.mist} strokeWidth={1.5} />
                </Pressable>
              ) : (
                <Toggle value={permStatus === 'granted'} onChange={handleNotifToggle} />
              )}
            </View>

            <View style={styles.divider} />

            {/* Sound toggle */}
            <View style={styles.row}>
              <View style={styles.rowLabel}>
                <Text variant="body" color={permStatus !== 'granted' ? 'mist' : 'ink'}>
                  Notification sound
                </Text>
              </View>
              <Toggle
                value={soundEnabled && permStatus === 'granted'}
                onChange={handleSoundToggle}
              />
            </View>
          </View>
        </View>

        {/* App section */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            APP
          </Text>
          <View style={styles.card}>
            {/* Timezone (read-only) */}
            <View style={styles.row}>
              <View style={styles.rowLabel}>
                <Text variant="body" color="ink">Timezone</Text>
                <Text variant="caption" color="mist">{timezone}</Text>
              </View>
              <Text variant="bodySmall" color="mist">Auto</Text>
            </View>

            <View style={styles.divider} />

            {/* History link */}
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={() => router.push('/history')}
              accessibilityLabel="View history"
              accessibilityRole="button"
            >
              <Text variant="body" color="ink" style={{ flex: 1 }}>Log history</Text>
              <ChevronRight size={16} color={tokens.mist} strokeWidth={1.5} />
            </Pressable>
          </View>
        </View>

        {/* Data section */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            DATA
          </Text>
          <View style={styles.card}>
            {/* Export */}
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={handleExport}
              accessibilityLabel="Export your data as JSON"
              accessibilityRole="button"
            >
              <View style={styles.rowLabel}>
                <Text variant="body" color="ink">Export data</Text>
                <Text variant="caption" color="mist">
                  Download a JSON file of all your tracked items, logs, measurements, and lab reports.
                </Text>
              </View>
              <ChevronRight size={16} color={tokens.mist} strokeWidth={1.5} />
            </Pressable>

            <View style={styles.divider} />

            {/* Delete */}
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={handleDeleteData}
              accessibilityLabel="Delete all local data"
              accessibilityRole="button"
            >
              <Trash2 size={18} color={tokens.critical} strokeWidth={1.5} />
              <Text variant="body" style={{ color: tokens.critical, flex: 1 }}>
                Delete all data
              </Text>
            </Pressable>
          </View>
        </View>

        {/* About section */}
        <View style={styles.section}>
          <Text variant="label" color="mist" style={styles.sectionLabel}>
            ABOUT
          </Text>
          <View style={styles.card}>
            <View style={styles.row}>
              <Text variant="body" color="ink" style={{ flex: 1 }}>Version</Text>
              <Text variant="bodySmall" color="mist">1.0.0 (Phase 1)</Text>
            </View>
            <View style={styles.divider} />
            <Pressable
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              onPress={() => Linking.openURL('https://kyros.health/privacy')}
              accessibilityLabel="Open privacy policy"
              accessibilityRole="button"
            >
              <Text variant="body" color="ink" style={{ flex: 1 }}>Privacy policy</Text>
              <ChevronRight size={16} color={tokens.mist} strokeWidth={1.5} />
            </Pressable>
          </View>
        </View>

        {/* Build info */}
        <Text variant="caption" color="mist" style={styles.buildInfo}>
          Vital · Phase 1
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.bone },
  content: {
    paddingHorizontal: tokens.s20,
    paddingTop: tokens.s24,
    paddingBottom: tokens.s48,
    gap: tokens.s32,
  },
  heading: {},
  section: { gap: tokens.s12 },
  sectionLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  card: {
    backgroundColor: tokens.paper,
    borderRadius: tokens.radii.card,
    borderWidth: 1,
    borderColor: tokens.hairline,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: tokens.s12,
    paddingHorizontal: tokens.s16,
    gap: tokens.s12,
  },
  rowLabel: { flex: 1, gap: tokens.s4 },
  divider: { height: 1, backgroundColor: tokens.hairline },
  buildInfo: { textAlign: 'center' },
});
