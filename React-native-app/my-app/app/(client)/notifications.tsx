import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useNotifications } from '../../contexts/NotificationContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Notification {
  id: number;
  // The backend (worker_connect.Notification via NotificationSerializer)
  // sends 'notification_type' and 'extra_data' - not 'type'/'data'. Reading
  // the wrong keys here meant n.type/n.data were always undefined, so every
  // notification silently fell back to the generic bell icon/color and
  // tapping one never navigated anywhere.
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  extra_data?: any;
}

export default function ClientNotificationsScreen() {
  const { theme, isDark } = useTheme();
  const { refreshUnreadCount } = useNotifications();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  useEffect(() => {
    loadNotifications();
  }, [filter]);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const data = await apiService.getNotifications(filter === 'unread');
      setNotifications(data.results || data || []);
    } catch (error) {
      console.error('Error loading notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadNotifications();
    await refreshUnreadCount();
    setRefreshing(false);
  };

  const handleMarkAsRead = async (id: number) => {
    try {
      await apiService.markNotificationAsRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      await refreshUnreadCount();
    } catch {}
  };

  const handleMarkAllAsRead = async () => {
    try {
      await apiService.markAllNotificationsAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      await refreshUnreadCount();
    } catch {}
  };

  const handlePress = (n: Notification) => {
    if (!n.is_read) handleMarkAsRead(n.id);
    // extra_data uses 'service_request_id' consistently across every
    // service-request-related notification (see
    // NotificationService.notify_service_assigned/_accepted/_completed in
    // worker_connect/notification_service.py) - not 'request_id'.
    const d = n.extra_data || {};
    if ((n.notification_type === 'job_assigned' || n.notification_type === 'job_completed') && d.service_request_id) {
      router.push(`/(client)/service-request/${d.service_request_id}` as any);
    } else if (n.notification_type === 'message_received') {
      // No messaging/chat screen exists yet under (client)/ - navigating
      // here would be a guaranteed dead route. Notification is marked
      // read above; leave it at that until a client chat screen exists.
    }
  };

  const getIcon = (type: string): any => {
    switch (type) {
      case 'job_assigned': return 'person-add';
      case 'job_completed': return 'checkmark-circle';
      case 'payment_received': return 'cash';
      case 'review_received': return 'star';
      case 'message_received': return 'chatbubble';
      case 'system_alert': return 'alert-circle';
      case 'promotion': return 'megaphone';
      default: return 'notifications';
    }
  };

  const getColor = (type: string) => {
    switch (type) {
      case 'job_completed': case 'payment_received': return '#10B981';
      case 'message_received': return '#3B82F6';
      case 'job_assigned': return '#8B5CF6';
      case 'review_received': return '#F59E0B';
      default: return theme.primary;
    }
  };

  const formatTime = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;
  const shown = filter === 'unread' ? notifications.filter(n => !n.is_read) : notifications;

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    content: { flex: 1 },
    header: {
      flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
      paddingHorizontal: 16, paddingVertical: 12,
    },
    titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    title: { fontSize: 20, fontFamily: 'Poppins_700Bold', color: theme.text },
    markAllBtn: {
      backgroundColor: theme.primary, borderRadius: 8,
      paddingHorizontal: 12, paddingVertical: 6,
    },
    markAllText: { fontSize: 12, fontFamily: 'Poppins_600SemiBold', color: '#fff' },
    tabs: {
      flexDirection: 'row', borderBottomWidth: 1,
      borderBottomColor: isDark ? '#2a2a2a' : '#e5e7eb',
    },
    tab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
    tabText: { fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
    scroll: { flex: 1 },
    scrollContent: { padding: 16, paddingBottom: 32 },
    card: {
      flexDirection: 'row', alignItems: 'flex-start',
      borderRadius: 14, padding: 14, marginBottom: 10,
      borderLeftWidth: 3,
      shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
    },
    iconWrap: {
      width: 44, height: 44, borderRadius: 12,
      alignItems: 'center', justifyContent: 'center', marginRight: 12,
    },
    cardBody: { flex: 1 },
    cardTitle: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginBottom: 3 },
    cardMsg: { fontSize: 13, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, lineHeight: 18 },
    cardTime: { fontSize: 11, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, marginTop: 4 },
    unreadDot: { width: 8, height: 8, borderRadius: 4, marginTop: 4 },
    empty: { alignItems: 'center', paddingTop: 60 },
    emptyTitle: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginTop: 12 },
    emptySub: { fontSize: 14, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, marginTop: 6, textAlign: 'center' },
    loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  });

  return (
    <View style={s.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title="Notifications" />

      <View style={s.content}>
        <View style={s.header}>
          <View style={s.titleRow}>
            <Ionicons name="notifications" size={24} color={theme.primary} />
            <Text style={s.title}>Notifications</Text>
          </View>
          {unreadCount > 0 && (
            <TouchableOpacity style={s.markAllBtn} onPress={handleMarkAllAsRead}>
              <Text style={s.markAllText}>Mark all read</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={s.tabs}>
          {(['all', 'unread'] as const).map(tab => (
            <TouchableOpacity
              key={tab}
              style={[s.tab, filter === tab && { borderBottomWidth: 2, borderBottomColor: theme.primary }]}
              onPress={() => setFilter(tab)}
            >
              <Text style={[s.tabText, { color: filter === tab ? theme.primary : theme.textSecondary }]}>
                {tab === 'all' ? `All (${notifications.length})` : `Unread (${unreadCount})`}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <View style={s.loader}>
            <ActivityIndicator size="large" color={theme.primary} />
          </View>
        ) : shown.length === 0 ? (
          <View style={s.empty}>
            <Ionicons name="notifications-outline" size={56} color={theme.textSecondary} />
            <Text style={s.emptyTitle}>{filter === 'unread' ? "You're all caught up!" : 'No Notifications'}</Text>
            <Text style={s.emptySub}>
              {filter === 'unread' ? 'No unread notifications.' : "You'll see notifications here when they arrive."}
            </Text>
          </View>
        ) : (
          <ScrollView
            style={s.scroll}
            contentContainerStyle={s.scrollContent}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />}
          >
            {shown.map(n => {
              const color = getColor(n.notification_type);
              return (
                <TouchableOpacity
                  key={n.id}
                  style={[s.card, {
                    backgroundColor: n.is_read ? theme.surface : (isDark ? 'rgba(15,118,110,0.1)' : '#F0FDF4'),
                    borderLeftColor: color,
                  }]}
                  onPress={() => handlePress(n)}
                  activeOpacity={0.75}
                >
                  <View style={[s.iconWrap, { backgroundColor: color + '20' }]}>
                    <Ionicons name={getIcon(n.notification_type)} size={22} color={color} />
                  </View>
                  <View style={s.cardBody}>
                    <Text style={s.cardTitle}>{n.title}</Text>
                    <Text style={s.cardMsg}>{n.message}</Text>
                    <Text style={s.cardTime}>{formatTime(n.created_at)}</Text>
                  </View>
                  {!n.is_read && <View style={[s.unreadDot, { backgroundColor: theme.primary }]} />}
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        )}
      </View>
    </View>
  );
}
