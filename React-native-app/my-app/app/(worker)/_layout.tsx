import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Tabs } from 'expo-router';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

export default function WorkerLayout() {
  const insets = useSafeAreaInsets();
  const { theme, isDark } = useTheme();
  const { t } = useTranslation();
  
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textSecondary,
        tabBarStyle: {
          backgroundColor: theme.surface,
          borderTopWidth: 1,
          borderTopColor: theme.border,
          // room for icon + label, plus the phone's own bottom area (iPhone home bar,
          // Android gesture bar) - a fixed 60 clipped the labels
          height: 68 + insets.bottom,
          paddingBottom: 8 + insets.bottom,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          lineHeight: 15,
          fontFamily: 'Poppins_600SemiBold',
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: t('nav.home'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="service-assignments"
        options={{
          title: t('nav.assignments'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="clipboard" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="messages"
        options={{
          title: t('nav.messages'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="chatbubbles" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t('nav.profile'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person" size={size} color={color} />
          ),
        }}
      />
      
      {/* Hidden screens - not shown in tab bar */}
      <Tabs.Screen name="jobs" options={{ href: null }} />
      <Tabs.Screen name="active-service" options={{ href: null }} />
      <Tabs.Screen name="activity" options={{ href: null }} />
      <Tabs.Screen name="analytics" options={{ href: null }} />
      <Tabs.Screen name="browse-jobs" options={{ href: null }} />
      <Tabs.Screen name="change-password" options={{ href: null }} />
      <Tabs.Screen name="cv" options={{ href: null }} />
      <Tabs.Screen name="data-retention" options={{ href: null }} />
      <Tabs.Screen name="documents" options={{ href: null }} />
      <Tabs.Screen name="earnings" options={{ href: null }} />
      <Tabs.Screen name="help" options={{ href: null }} />
      <Tabs.Screen name="notifications" options={{ href: null }} />
      <Tabs.Screen name="payout-methods" options={{ href: null }} />
      <Tabs.Screen name="privacy" options={{ href: null }} />
      <Tabs.Screen name="privacy-settings" options={{ href: null }} />
      <Tabs.Screen name="profile-edit" options={{ href: null }} />
      <Tabs.Screen name="profile-setup" options={{ href: null }} />
      <Tabs.Screen name="saved-jobs" options={{ href: null }} />
      <Tabs.Screen name="settings" options={{ href: null }} />
      <Tabs.Screen name="support" options={{ href: null }} />

      {/* Folder routes - dynamic/nested screens */}
      <Tabs.Screen name="assignments/pending" options={{ href: null }} />
      <Tabs.Screen name="assignments/clock/in/[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/clock/out/[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/complete/[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/respond/[id]" options={{ href: null }} />
      <Tabs.Screen name="service-assignment/[id]" options={{ href: null }} />
      <Tabs.Screen name="conversation/[id]" options={{ href: null }} />
      <Tabs.Screen name="job/[id]" options={{ href: null }} />
      <Tabs.Screen name="experience/add" options={{ href: null }} />
      <Tabs.Screen name="experience/index" options={{ href: null }} />
      <Tabs.Screen name="experience/[id]/edit" options={{ href: null }} />
      {/* job posts (vacancies) */}
      <Tabs.Screen name="find-jobs" options={{ href: null }} />
      <Tabs.Screen name="my-applications" options={{ href: null }} />
      <Tabs.Screen name="vacancy/[id]" options={{ href: null }} />
      <Tabs.Screen name="contracts" options={{ href: null }} />
      <Tabs.Screen name="contract/[id]" options={{ href: null }} />
      {/* direct hire (a client books one worker) */}
      <Tabs.Screen name="direct-hires" options={{ href: null }} />
      <Tabs.Screen name="direct-hire/[id]" options={{ href: null }} />
    </Tabs>
  );
}
