import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface Activity {
  id: number;
  activity_type: string;
  description: string;
  created_at: string;
  service_request?: {
    id: number;
    title: string;
    category_name: string;
  };
  location?: string;
}

export default function ActivityHistoryScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    thisWeek: 0,
    thisMonth: 0,
  });

  useFocusEffect(
    useCallback(() => {
      loadActivity();
    }, [])
  );

  const loadActivity = async () => {
    try {
      setLoading(true);
      const response = await apiService.getWorkerActivity();
      setActivities(response.results || response.activities || []);
      
      // Calculate stats
      const now = new Date();
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      
      const thisWeek = (response.results || response.activities || []).filter(
        (a: Activity) => new Date(a.created_at) > weekAgo
      ).length;
      
      const thisMonth = (response.results || response.activities || []).filter(
        (a: Activity) => new Date(a.created_at) > monthAgo
      ).length;
      
      setStats({
        total: (response.results || response.activities || []).length,
        thisWeek,
        thisMonth,
      });
    } catch (error: any) {
      console.error('Error loading activity:', error);
      Alert.alert(t('common.error'), t('activity.failedLoadActivity'));
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadActivity();
    setRefreshing(false);
  };

  const getActivityIcon = (type: string) => {
    const icons: { [key: string]: any } = {
      accepted: 'checkmark-circle',
      rejected: 'close-circle',
      clock_in: 'time',
      clock_out: 'stop-circle',
      completed: 'checkmark-done-circle',
      assignment: 'briefcase',
    };
    return icons[type] || 'ellipse';
  };

  const getActivityColor = (type: string) => {
    const colors: { [key: string]: string } = {
      accepted: '#4CAF50',
      rejected: '#F44336',
      clock_in: '#2196F3',
      clock_out: '#FF9800',
      completed: '#4CAF50',
      assignment: '#9C27B0',
    };
    return colors[type] || theme.textSecondary;
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 1) {
      const minutes = Math.floor(diff / (1000 * 60));
      return minutes < 1 ? 'Just now' : `${minutes}m ago`;
    }
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const groupActivitiesByDate = () => {
    const groups: { [key: string]: Activity[] } = {};
    
    activities.forEach((activity) => {
      const date = new Date(activity.created_at);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      let groupKey: string;
      if (date.toDateString() === today.toDateString()) {
        groupKey = 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        groupKey = 'Yesterday';
      } else {
        groupKey = date.toLocaleDateString('en-US', {
          month: 'long',
          day: 'numeric',
          year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
        });
      }
      
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(activity);
    });
    
    return groups;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Activity History" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>{t('activity.loadingActivity')}</Text>
        </View>
      </View>
    );
  }

  const groupedActivities = groupActivitiesByDate();

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Activity History" showBack />

      {/* Stats Cards */}
      <View style={styles.statsContainer}>
        <View style={[styles.statCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.statValue, { color: theme.primary }]}>
            {stats.total}
          </Text>
          <Text style={[styles.statLabel, { color: theme.textSecondary }]}>{t('activity.total')}</Text>
        </View>

        <View style={[styles.statCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.statValue, { color: theme.primary }]}>
            {stats.thisWeek}
          </Text>
          <Text style={[styles.statLabel, { color: theme.textSecondary }]}>{t('activity.thisWeek')}</Text>
        </View>

        <View style={[styles.statCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.statValue, { color: theme.primary }]}>
            {stats.thisMonth}
          </Text>
          <Text style={[styles.statLabel, { color: theme.textSecondary }]}>{t('activity.thisMonth')}</Text>
        </View>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {activities.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="calendar-outline" size={64} color={theme.textSecondary} />
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>{t('activity.noActivity')}</Text>
            <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>{t('activity.workHistoryWillAppear')}</Text>
          </View>
        ) : (
          <View style={styles.activityList}>
            {Object.entries(groupedActivities).map(([dateGroup, groupActivities]) => (
              <View key={dateGroup} style={styles.dateGroup}>
                <Text style={[styles.dateHeader, { color: theme.text }]}>
                  {dateGroup}
                </Text>

                {groupActivities.map((activity, index) => (
                  <View
                    key={activity.id}
                    style={[styles.activityCard, { backgroundColor: theme.card }]}
                  >
                    <View style={styles.activityLeft}>
                      <View
                        style={[
                          styles.activityIcon,
                          { backgroundColor: getActivityColor(activity.activity_type) + '20' },
                        ]}
                      >
                        <Ionicons
                          name={getActivityIcon(activity.activity_type)}
                          size={24}
                          color={getActivityColor(activity.activity_type)}
                        />
                      </View>
                      {index < groupActivities.length - 1 && (
                        <View style={[styles.timeline, { backgroundColor: theme.border }]} />
                      )}
                    </View>

                    <View style={styles.activityContent}>
                      <Text style={[styles.activityDescription, { color: theme.text }]}>
                        {activity.description}
                      </Text>

                      {activity.service_request && (
                        <View style={[styles.serviceTag, { backgroundColor: theme.background }]}>
                          <Ionicons name="briefcase-outline" size={14} color={theme.textSecondary} />
                          <Text
                            style={[styles.serviceTitle, { color: theme.textSecondary }]}
                            numberOfLines={1}
                          >
                            {activity.service_request.title}
                          </Text>
                        </View>
                      )}

                      {activity.location && (
                        <View style={styles.locationRow}>
                          <Ionicons name="location-outline" size={12} color={theme.textSecondary} />
                          <Text style={[styles.locationText, { color: theme.textSecondary }]}>
                            {activity.location}
                          </Text>
                        </View>
                      )}

                      <Text style={[styles.activityTime, { color: theme.textSecondary }]}>
                        {formatDateTime(activity.created_at)}
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
  },
  statsContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  statCard: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statValue: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
  },
  content: {
    flex: 1,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 60,
    paddingHorizontal: 32,
  },
  emptyText: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  activityList: {
    padding: 16,
  },
  dateGroup: {
    marginBottom: 24,
  },
  dateHeader: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  activityCard: {
    flexDirection: 'row',
    padding: 12,
    borderRadius: 12,
    marginBottom: 2,
  },
  activityLeft: {
    alignItems: 'center',
    marginRight: 12,
  },
  activityIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  timeline: {
    width: 2,
    flex: 1,
    marginVertical: 4,
  },
  activityContent: {
    flex: 1,
    paddingTop: 4,
  },
  activityDescription: {
    fontSize: 14,
    marginBottom: 6,
    lineHeight: 20,
  },
  serviceTag: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 4,
    gap: 4,
  },
  serviceTitle: {
    fontSize: 12,
    maxWidth: 200,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    gap: 4,
  },
  locationText: {
    fontSize: 11,
  },
  activityTime: {
    fontSize: 11,
    fontStyle: 'italic',
  },
});
