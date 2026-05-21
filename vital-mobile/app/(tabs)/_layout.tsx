import { Tabs } from 'expo-router';
import { View } from 'react-native';
import { Home, Layers, Activity, Settings } from 'lucide-react-native';
import { tokens } from '../../src/theme/tokens';

// Each tab icon wraps the lucide icon with a 2px vertical accent bar on the left
// when focused (editorial clinical active indicator — no pill backgrounds).
function TabIcon({
  icon: Icon,
  focused,
  color,
  size,
}: {
  icon: typeof Home;
  focused: boolean;
  color: string;
  size: number;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
      <View
        style={{
          width: 2,
          height: 18,
          borderRadius: 1,
          backgroundColor: focused ? tokens.categoryColors.medication : 'transparent',
          marginRight: 5,
        }}
      />
      <Icon color={color} size={size} strokeWidth={1.5} />
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: tokens.bone,
          borderTopWidth: 1,
          borderTopColor: tokens.hairline,
          height: 56,
          elevation: 0,
          shadowOpacity: 0,
        },
        tabBarActiveTintColor: tokens.ink,
        tabBarInactiveTintColor: tokens.mist,
        tabBarLabelStyle: {
          fontFamily: 'GeistSans-Medium',
          fontSize: 10,
          marginBottom: 2,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Today',
          tabBarIcon: ({ color, size, focused }) => (
            <TabIcon icon={Home} focused={focused} color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="library"
        options={{
          title: 'Library',
          tabBarIcon: ({ color, size, focused }) => (
            <TabIcon icon={Layers} focused={focused} color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="insights"
        options={{
          title: 'Insights',
          tabBarIcon: ({ color, size, focused }) => (
            <TabIcon icon={Activity} focused={focused} color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color, size, focused }) => (
            <TabIcon icon={Settings} focused={focused} color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
