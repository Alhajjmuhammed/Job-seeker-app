import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNetInfo } from '@react-native-community/netinfo';
import { useTranslation } from 'react-i18next';

/**
 * Red "You are offline" bar - only when the phone really has no internet.
 *
 * It used to follow the live-updates WebSocket instead, so whenever that one
 * channel dropped (or a network blocked it) the bar said "offline" while the
 * app itself worked fine: every screen still loads and refreshes over normal
 * requests. Losing instant updates is not being offline.
 */
export default function ConnectionStatus() {
  const { t } = useTranslation();
  const net = useNetInfo();

  // null = not known yet: say nothing rather than flash a false alarm.
  // isInternetReachable is not used: its probe (a Google URL) can be blocked
  // in browsers and on some networks, which would show a false "offline".
  const offline = net.isConnected === false;
  if (!offline) {
    return null;
  }

  return (
    <View style={[styles.container, { backgroundColor: '#EF4444' }]}>
      <Ionicons name="cloud-offline-outline" size={14} color="#FFFFFF" />
      <Text style={styles.text}>{t('common.offline')}</Text>
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
