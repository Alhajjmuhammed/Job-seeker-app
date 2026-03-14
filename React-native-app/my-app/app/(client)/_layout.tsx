import { Tabs } from 'expo-router';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';

export default function ClientLayout() {
  const { theme } = useTheme();
  
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textSecondary,
        tabBarStyle: {
          backgroundColor: theme.card,
          borderTopWidth: 1,
          borderTopColor: theme.border,
          height: 60,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '600',
          fontFamily: 'Poppins_600SemiBold',
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: 'Search',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="search" size={size} color={color} />
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
      {/* Hidden routes */}
      <Tabs.Screen name="change-password" options={{ href: null }} />
      <Tabs.Screen name="data-retention" options={{ href: null }} />
      <Tabs.Screen name="favorites" options={{ href: null }} />
      <Tabs.Screen name="jobs" options={{ href: null }} />
      <Tabs.Screen name="my-requests" options={{ href: null }} />
      <Tabs.Screen name="notifications" options={{ href: null }} />
      <Tabs.Screen name="payment-methods" options={{ href: null }} />
      <Tabs.Screen name="privacy-settings" options={{ href: null }} />
      <Tabs.Screen name="profile-edit" options={{ href: null }} />
      <Tabs.Screen name="request-service" options={{ href: null }} />
      <Tabs.Screen name="settings" options={{ href: null }} />
      <Tabs.Screen name="conversation/[id]" options={{ href: null }} />
      <Tabs.Screen name="job/[id]" options={{ href: null }} />
      <Tabs.Screen name="request-service/[id]" options={{ href: null }} />
      <Tabs.Screen name="service-request/[id]" options={{ href: null }} />
      <Tabs.Screen name="edit-service-request/[id]" options={{ href: null }} />
      <Tabs.Screen name="rate-worker/[id]" options={{ href: null }} />
    </Tabs>
  );
}
