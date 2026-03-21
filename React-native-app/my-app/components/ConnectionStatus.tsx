import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useTheme } from '../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

export default function ConnectionStatus() {
  const { connected, connectionState } = useWebSocket();
  const { theme } = useTheme();
  const { t } = useTranslation();

  // WebSocket is now enabled - show connection status when not connected
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
        return t('common.connecting');
      case 'disconnected':
        return t('common.offline');
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

  // Only show when not connected (to avoid clutter when everything is working)
  if (connectionState === 'connected') {
    return null;
  }

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
