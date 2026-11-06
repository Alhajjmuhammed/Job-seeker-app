/**
 * Chat list - shared by the worker and the client app.
 * The server lists support plus every worker/client whose job was accepted;
 * phone_number is filled only for those accepted-job contacts (call button).
 */
import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, ActivityIndicator,
  RefreshControl, Alert, Linking,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface Conversation {
  id: number;
  name: string;
  user_type: string;
  last_message: string;
  last_message_time: string | null;
  unread_count: number;
  about?: string;
  can_send?: boolean;
  phone_number?: string;
}

export default function ConversationList({ group }: { group: '(worker)' | '(client)' }) {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const load = useCallback(async (quiet = false) => {
    try {
      const data = await apiService.getConversations();
      setConversations(data.conversations || []);
    } catch (error: any) {
      if (!quiet && error?.response?.status !== 404) {
        Alert.alert(t('common.error'), t('messages.failedLoadConversations'));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Reload whenever the list comes back on screen, and every 15 s while it is.
  useFocusEffect(
    useCallback(() => {
      load(true);
      const timer = setInterval(() => load(true), 15000);
      return () => clearInterval(timer);
    }, [load])
  );

  const open = (c: Conversation) =>
    router.push(`/${group}/conversation/${c.id}?name=${encodeURIComponent(c.name || '')}` as any);

  const call = (phone: string) =>
    Linking.openURL(`tel:${phone}`).catch(() => Alert.alert(t('common.error'), t('messages.cannotCall')));

  const roleLabel = (type: string) =>
    type === 'admin' ? t('messages.support') : type === 'worker' ? t('messages.worker') : t('messages.client');

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const mins = Math.floor((Date.now() - date.getTime()) / 60000);
    if (mins < 1) return t('messages.justNow');
    if (mins < 60) return `${mins}m`;
    if (mins < 24 * 60) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const q = searchQuery.trim().toLowerCase();
  const shown = conversations.filter(c =>
    !q || (c.name || '').toLowerCase().includes(q) || (c.about || '').toLowerCase().includes(q));

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header />

      <View style={[styles.searchContainer, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        <TextInput
          style={[styles.searchInput, { backgroundColor: theme.background, color: theme.text }]}
          placeholder={t('messages.searchConversations')}
          placeholderTextColor={theme.textSecondary}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {loading ? (
        <View style={styles.loadingContainer}><ActivityIndicator size="large" color={theme.primary} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}
          refreshControl={<RefreshControl refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }} colors={[theme.primary]} />}>
          {shown.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="chatbubbles-outline" size={48} color={theme.textSecondary} style={{ marginBottom: 12 }} />
              <Text style={[styles.emptyText, { color: theme.text }]}>{t('messages.noConversations')}</Text>
              <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>{t('messages.chatAfterAccept')}</Text>
            </View>
          ) : shown.map((c) => {
            const isSupport = c.user_type === 'admin';
            const accent = isSupport ? '#0B3D33' : c.user_type === 'worker' ? '#7C3AED' : '#2563EB';
            return (
              <TouchableOpacity key={c.id} onPress={() => open(c)}
                style={[styles.card, { backgroundColor: theme.surface },
                  isDark ? {} : { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 }]}>
                <View style={[styles.avatar, { backgroundColor: accent }]}>
                  {isSupport ? <Ionicons name="headset" size={22} color="#FFFFFF" />
                    : <Text style={styles.avatarText}>{(c.name || '?').substring(0, 1).toUpperCase()}</Text>}
                </View>
                <View style={styles.body}>
                  <View style={styles.row}>
                    <Text style={[styles.name, { color: theme.text }]} numberOfLines={1}>
                      {isSupport ? t('messages.supportTeam') : c.name}
                    </Text>
                    <Text style={[styles.time, { color: c.unread_count ? theme.primary : theme.textSecondary }]}>
                      {formatTime(c.last_message_time)}
                    </Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={[styles.preview, { color: c.unread_count ? theme.text : theme.textSecondary }]} numberOfLines={1}>
                      <Text style={{ color: accent, fontFamily: 'Poppins_600SemiBold' }}>{roleLabel(c.user_type)} · </Text>
                      {c.last_message || c.about || t('messages.sayHello')}
                    </Text>
                    {c.unread_count > 0 && (
                      <View style={[styles.unread, { backgroundColor: theme.primary }]}>
                        <Text style={styles.unreadText}>{c.unread_count > 9 ? '9+' : c.unread_count}</Text>
                      </View>
                    )}
                  </View>
                </View>
                {!!c.phone_number && (
                  <TouchableOpacity onPress={() => call(c.phone_number!)} style={[styles.callIcon, { backgroundColor: theme.primary }]}
                    accessibilityLabel={t('messages.call')} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                    <Ionicons name="call" size={18} color="#FFFFFF" />
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  searchContainer: { paddingHorizontal: 20, paddingVertical: 12, borderBottomWidth: 1 },
  searchInput: { height: 40, borderRadius: 10, paddingHorizontal: 16, fontSize: 15, fontFamily: 'Poppins_400Regular' },
  scrollContent: { padding: 16 },
  card: { flexDirection: 'row', borderRadius: 12, padding: 14, marginBottom: 10, alignItems: 'center' },
  avatar: { width: 48, height: 48, borderRadius: 24, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  avatarText: { color: '#FFFFFF', fontSize: 18, fontFamily: 'Poppins_700Bold' },
  body: { flex: 1, minWidth: 0 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  name: { flex: 1, fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  time: { fontSize: 11, fontFamily: 'Poppins_400Regular' },
  preview: { flex: 1, fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  unread: { borderRadius: 10, minWidth: 20, height: 20, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 5 },
  unreadText: { color: '#FFFFFF', fontSize: 11, fontFamily: 'Poppins_700Bold' },
  callIcon: { width: 38, height: 38, borderRadius: 19, justifyContent: 'center', alignItems: 'center', marginLeft: 10 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 50 },
  emptyState: { padding: 50, alignItems: 'center' },
  emptyText: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  emptySubtext: { fontSize: 14, fontFamily: 'Poppins_400Regular', textAlign: 'center' },
});
