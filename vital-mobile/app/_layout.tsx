import { Stack, router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts } from 'expo-font';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { registerNotificationCategories } from '../src/notifications/categories';
import { registerNotificationHandlers } from '../src/notifications/handlers';
import { useNotificationSync } from '../src/hooks/useNotificationSync';
import { storage } from '../src/utils/storage';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, staleTime: 30_000 },
  },
});

function AppShell({ children }: { children: React.ReactNode }) {
  useNotificationSync();
  return <>{children}</>;
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    'Fraunces-Variable': {
      uri: 'https://fonts.gstatic.com/s/fraunces/v31/6NUh8FyLNQOQZAnv9bYEvDiIdE9Eqcm369i3pCp5OqE6fgHYE.woff2',
    },
    'GeistSans-Regular': {
      uri: 'https://fonts.gstatic.com/s/geist/v1/gyBhhwUxId8hqL4FySQ1SFHKQJvF8gXGOhGo9G4.woff2',
    },
    'GeistSans-Medium': {
      uri: 'https://fonts.gstatic.com/s/geist/v1/gyBhhwUxId8hqL4FySQ1SFHKQJvF8gXGOhGo9G4.woff2',
    },
    'GeistSans-SemiBold': {
      uri: 'https://fonts.gstatic.com/s/geist/v1/gyBhhwUxId8hqL4FySQ1SFHKQJvF8gXGOhGo9G4.woff2',
    },
    'GeistMono-Regular': {
      uri: 'https://fonts.gstatic.com/s/geistmono/v1/or3yQ6P12-iJxAIgLa78DkrbXsDgk10_B7ZBDE8.woff2',
    },
    'GeistMono-Medium': {
      uri: 'https://fonts.gstatic.com/s/geistmono/v1/or3yQ6P12-iJxAIgLa78DkrbXsDgk10_B7ZBDE8.woff2',
    },
  });

  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  useEffect(() => {
    registerNotificationCategories().catch(() => {});
    const cleanup = registerNotificationHandlers();
    return cleanup;
  }, []);

  useEffect(() => {
    storage.getItem('vital_onboarded').then((v) => {
      setOnboardingDone(v === '1');
    });
  }, []);

  useEffect(() => {
    if ((fontsLoaded || fontError) && onboardingDone === false) {
      router.replace('/onboarding');
    }
  }, [fontsLoaded, fontError, onboardingDone]);

  const onLayoutRootView = useCallback(async () => {
    if (fontsLoaded || fontError) {
      await SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppShell>
          <View style={{ flex: 1 }} onLayout={onLayoutRootView}>
            <Stack screenOptions={{ headerShown: false }} />
          </View>
        </AppShell>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
