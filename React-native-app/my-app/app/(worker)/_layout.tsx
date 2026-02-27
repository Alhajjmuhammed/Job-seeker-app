import { Tabs } from 'expo-router';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';

export default function WorkerLayout() {
  const { theme, isDark } = useTheme();
  
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
          height: 60,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontFamily: 'Poppins_600SemiBold',
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="service-assignments"
        options={{
          title: 'Assignments',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="clipboard" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="jobs"
        options={{
          title: 'Jobs',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="briefcase" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="messages"
        options={{
          title: 'Messages',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="chatbubbles" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person" size={size} color={color} />
          ),
        }}
      />
      
      {/* Hidden screens - not shown in tab bar */}
      <Tabs.Screen name="active-service" options={{ href: null }} />
      <Tabs.Screen name="activity" options={{ href: null }} />
      <Tabs.Screen name="analytics" options={{ href: null }} />
      <Tabs.Screen name="applications" options={{ href: null }} />
      <Tabs.Screen name="browse-jobs" options={{ href: null }} />
      <Tabs.Screen name="documents" options={{ href: null }} />
      <Tabs.Screen name="earnings" options={{ href: null }} />
      <Tabs.Screen name="help" options={{ href: null }} />
      <Tabs.Screen name="notifications" options={{ href: null }} />
      <Tabs.Screen name="privacy" options={{ href: null }} />
      <Tabs.Screen name="profile-edit" options={{ href: null }} />
      <Tabs.Screen name="profile-setup" options={{ href: null }} />
      <Tabs.Screen name="saved-jobs" options={{ href: null }} />
      <Tabs.Screen name="settings" options={{ href: null }} />
      <Tabs.Screen name="support" options={{ href: null }} />
      <Tabs.Screen name="terms" options={{ href: null }} />
      
      {/* Folder routes - dynamic/nested screens */}
      <Tabs.Screen name="assignments/pending" options={{ href: null }} />
      <Tabs.Screen name="assignments/clock/in-[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/clock/out-[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/complete/[id]" options={{ href: null }} />
      <Tabs.Screen name="assignments/respond/[id]" options={{ href: null }} />
      <Tabs.Screen name="service-assignment/[id]" options={{ href: null }} />
      <Tabs.Screen name="conversation/[id]" options={{ href: null }} />
      <Tabs.Screen name="job/[id]" options={{ href: null }} />
      <Tabs.Screen name="job/[id]/apply" options={{ href: null }} />
      <Tabs.Screen name="experience/add" options={{ href: null }} />
      <Tabs.Screen name="experience/index" options={{ href: null }} />
      <Tabs.Screen name="experience/[id]/edit" options={{ href: null }} />
    </Tabs>
  );
}
