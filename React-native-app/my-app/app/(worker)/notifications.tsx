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
import { useTranslation } from 'react-i18next';

interface Notification {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  extra_data?: any;
}

export default function NotificationsScreen() {
  const { t } = useTranslation();
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

    // Navigate based on type. These keys mirror what the server actually
    // sends: the payload field is extra_data (not data), and the vocabulary is
    // the notification_type choices on the Notification model.
    const data = notification.extra_data || {};
    const assignmentId = data.assignment_id;
    const requestId = data.service_request_id ?? data.request_id ?? data.job_id;
    switch (notification.notification_type) {
      case 'job_assigned':
        if (assignmentId) {
          router.push(`/(worker)/service-assignment/${assignmentId}` as any);
        } else if (requestId) {
          router.push(`/(worker)/service-assignment/${requestId}` as any);
        } else {
          router.push('/(worker)/jobs' as any);
        }
        break;
      case 'job_accepted':
      case 'job_rejected':
      case 'job_application':
        router.push('/(worker)/jobs' as any);
        break;
      case 'job_completed':
      case 'payment_received':
        router.push('/(worker)/earnings' as any);
        break;
      case 'message_received':
        if (data.sender_id ?? data.user_id) {
          router.push(`/(worker)/conversation/${data.sender_id ?? data.user_id}` as any);
        } else {
          router.push('/(worker)/messages' as any);
        }
        break;
      default:
        // account_update, document_verified, promotion, review_received, system_alert
        router.push('/(worker)/dashboard' as any);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'job_assigned':
        return 'briefcase';
      case 'job_accepted':
        return 'checkmark-circle';
      case 'job_rejected':
      case 'system_alert':
        return 'close-circle';
      case 'message_received':
        return 'chatbubble';
      case 'job_application':
        return 'person-add';
      case 'payment_received':
        return 'cash';
      case 'job_completed':
        return 'ribbon';
      case 'review_received':
        return 'star';
      case 'document_verified':
        return 'shield-checkmark';
      case 'promotion':
        return 'megaphone';
      default:
        return 'notifications';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'job_accepted':
      case 'payment_received':
      case 'job_completed':
      case 'review_received':
      case 'document_verified':
        return '#10B981';
      case 'job_rejected':
      case 'system_alert':
        return '#EF4444';
      case 'message_received':
        return '#3B82F6';
      case 'job_application':
      case 'job_assigned':
        return '#8B5CF6';
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
      <Header showBack />

      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Ionicons name="notifications" size={28} color={theme.primary} />
            <Text style={[styles.title, { color: theme.text }]}>{t('nav.notifications')}</Text>
          </View>
          
          {unreadCount > 0 && (
            <TouchableOpacity
              style={[styles.markAllButton, { backgroundColor: theme.primary }]}
              onPress={handleMarkAllAsRead}
            >
              <Text style={styles.markAllButtonText}>{t('notifications.markAllRead')}</Text>
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
                { color: filter === 'all' ? theme.primary : theme.textSecondary },
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
                { color: filter === 'unread' ? theme.primary : theme.textSecondary },
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
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>{t('notifications.loadingNotifications')}</Text>
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
                <Text style={[styles.emptyTitle, { color: theme.text }]}>
                  No {filter === 'unread' ? 'Unread ' : ''}Notifications
                </Text>
                <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
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
                      borderLeftColor: getNotificationColor(notification.notification_type),
                    },
                  ]}
                  onPress={() => handleNotificationPress(notification)}
                >
                  <View
                    style={[
                      styles.iconContainer,
                      { backgroundColor: getNotificationColor(notification.notification_type) + '20' },
                    ]}
                  >
                    <Ionicons
                      name={getNotificationIcon(notification.notification_type) as any}
                      size={24}
                      color={getNotificationColor(notification.notification_type)}
                    />
                  </View>

                  <View style={styles.notificationContent}>
                    <Text style={[styles.notificationTitle, { color: theme.text }]}>
                      {notification.title}
                    </Text>
                    <Text style={[styles.notificationMessage, { color: theme.textSecondary }]}>
                      {notification.message}
                    </Text>
                    <Text style={[styles.notificationTime, { color: theme.textSecondary }]}>
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
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
  },
  markAllButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  markAllButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
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
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  notificationMessage: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
    marginBottom: 6,
  },
  notificationTime: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
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
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
  },
});
