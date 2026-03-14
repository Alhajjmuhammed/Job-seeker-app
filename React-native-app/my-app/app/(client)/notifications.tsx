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
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  data?: any;
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

  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await apiService.markNotificationAsRead(notificationId);
      setNotifications(prev =>
        prev.map(n => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      await refreshUnreadCount();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await apiService.markAllNotificationsAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      await refreshUnreadCount();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  const handleNotificationPress = (notification: Notification) => {
    // Mark as read
    if (!notification.is_read) {
      handleMarkAsRead(notification.id);
    }

    // Navigate based on type - CLIENT-SPECIFIC ROUTES
    const data = notification.data || {};
    if (notification.type === 'service_request_update' || notification.type === 'worker_assigned') {
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      }
    } else if (notification.type === 'service_completed') {
      if (data.request_id) {
        router.push(`/(client)/rate-worker/${data.worker_id}` as any);
      }
    } else if (notification.type === 'payment_verified' || notification.type === 'payment_rejected') {
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      }
    } else if (notification.type === 'new_message') {
      if (data.user_id) {
        router.push(`/(client)/conversation/${data.user_id}` as any);
      } else {
        router.push('/(client)/messages' as any);
      }
    } else if (notification.type === 'request_cancelled' || notification.type === 'request_accepted') {
      router.push('/(client)/my-requests' as any);
    } else {
      // Default: go to dashboard
      router.push('/(client)/dashboard' as any);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'service_request_update':
      case 'request_accepted':
        return 'checkmark-circle';
      case 'request_cancelled':
        return 'close-circle';
      case 'worker_assigned':
        return 'person-add';
      case 'service_completed':
        return 'ribbon';
      case 'payment_verified':
        return 'cash';
      case 'payment_rejected':
        return 'close-circle';
      case 'new_message':
        return 'chatbubble';
      default:
        return 'notifications';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'request_accepted':
      case 'service_completed':
      case 'payment_verified':
      case 'worker_assigned':
        return '#10B981';
      case 'request_cancelled':
      case 'payment_rejected':
        return '#EF4444';
      case 'new_message':
        return '#3B82F6';
      case 'service_request_update':
        return '#F59E0B';
      default:
        return theme.primary;
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const filteredNotifications = notifications;
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Notifications" />

      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Ionicons name="notifications" size={28} color={theme.primary} />
            <Text style={[styles.title, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>
              Notifications
            </Text>
          </View>
          
          {unreadCount > 0 && (
            <TouchableOpacity
              style={[styles.markAllButton, { backgroundColor: theme.primary }]}
              onPress={handleMarkAllAsRead}
            >
              <Text style={[styles.markAllButtonText, { fontFamily: 'Poppins_600SemiBold' }]}>
                Mark all read
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Filter Tabs */}
        <View style={styles.filterTabs}>
          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'all' && { borderBottomColor: theme.primary, borderBottomWidth: 2 },
            ]}
            onPress={() => setFilter('all')}
          >
            <Text
              style={[
                styles.filterTabText,
                { 
                  color: filter === 'all' ? theme.primary : theme.textSecondary,
                  fontFamily: 'Poppins_600SemiBold'
                },
              ]}
            >
              All ({notifications.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.filterTab,
              filter === 'unread' && { borderBottomColor: theme.primary, borderBottomWidth: 2 },
            ]}
            onPress={() => setFilter('unread')}
          >
            <Text
              style={[
                styles.filterTabText,
                { 
                  color: filter === 'unread' ? theme.primary : theme.textSecondary,
                  fontFamily: 'Poppins_600SemiBold'
                },
              ]}
            >
              Unread ({unreadCount})
            </Text>
          </TouchableOpacity>
        </View>

        {/* Notifications List */}
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              Loading notifications...
            </Text>
          </View>
        ) : (
          <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.primary}
                colors={[theme.primary]}
              />
            }
          >
            {filteredNotifications.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons
                  name="notifications-outline"
                  size={56}
                  color={theme.textSecondary}
                  style={{ marginBottom: 16 }}
                />
                <Text style={[styles.emptyTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                  No {filter === 'unread' ? 'Unread ' : ''}Notifications
                </Text>
                <Text style={[styles.emptySubtitle, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  {filter === 'unread'
                    ? "You're all caught up!"
                    : "You'll see notifications here when you receive them"}
                </Text>
              </View>
            ) : (
              filteredNotifications.map((notification) => (
                <TouchableOpacity
                  key={notification.id}
                  style={[
                    styles.notificationCard,
                    {
                      backgroundColor: notification.is_read
                        ? theme.surface
                        : isDark
                        ? 'rgba(15, 118, 110, 0.1)'
                        : '#F0FDF4',
                      borderLeftColor: getNotificationColor(notification.type),
                    },
                  ]}
                  onPress={() => handleNotificationPress(notification)}
                >
                  <View
                    style={[
                      styles.iconContainer,
                      { backgroundColor: getNotificationColor(notification.type) + '20' },
                    ]}
                  >
                    <Ionicons
                      name={getNotificationIcon(notification.type) as any}
                      size={24}
                      color={getNotificationColor(notification.type)}
                    />
                  </View>

                  <View style={styles.notificationContent}>
                    <Text style={[styles.notificationTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                      {notification.title}
                    </Text>
                    <Text style={[styles.notificationMessage, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                      {notification.message}
                    </Text>
                    <Text style={[styles.notificationTime, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                      {formatTime(notification.created_at)}
                    </Text>
                  </View>

                  {!notification.is_read && (
                    <View style={[styles.unreadDot, { backgroundColor: theme.primary }]} />
                  )}
                </TouchableOpacity>
              ))
            )}
          </ScrollView>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize: 24,
  },
  markAllButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  markAllButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
  },
  filterTabs: {
    flexDirection: 'row',
    marginBottom: 20,
    gap: 24,
  },
  filterTab: {
    paddingVertical: 8,
  },
  filterTabText: {
    fontSize: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 15,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  notificationCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  notificationContent: {
    flex: 1,
  },
  notificationTitle: {
    fontSize: 15,
    marginBottom: 4,
  },
  notificationMessage: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 6,
  },
  notificationTime: {
    fontSize: 12,
  },
  unreadDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    alignSelf: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 15,
    textAlign: 'center',
  },
});
