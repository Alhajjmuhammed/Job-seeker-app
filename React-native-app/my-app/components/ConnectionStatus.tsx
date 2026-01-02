import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useTheme } from '../contexts/ThemeContext';

export default function ConnectionStatus() {
  const { connected, connectionState } = useWebSocket();
  const { theme } = useTheme();

  // Don't show anything - WebSocket is intentionally disabled in current setup
  // The app works fully without real-time WebSocket features
  return null;

  const getStatusColor = () => {
    switch (connectionState) {
      case 'connecting':
        return '#F59E0B'; // Yellow/orange
      case 'disconnected':
        return '#EF4444'; // Red
      default:
        return theme.textSecondary;
    }
  };

  const getStatusText = () => {
    switch (connectionState) {
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Offline';
      default:
        return '';
    }
  };

  const getStatusIcon = () => {
    switch (connectionState) {
      case 'connecting':
        return 'sync-outline';
      case 'disconnected':
        return 'cloud-offline-outline';
      default:
        return 'cloud-done-outline';
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: getStatusColor() }]}>
      <Ionicons name={getStatusIcon() as any} size={14} color="#FFFFFF" />
      <Text style={styles.text}>{getStatusText()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 4,
    paddingHorizontal: 12,
    gap: 6,
  },
  text: {
    color: '#FFFFFF',
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
});
