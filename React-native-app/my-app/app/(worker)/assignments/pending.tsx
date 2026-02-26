import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';

interface Assignment {
  id: number;
  title: string;
  category_name: string;
  status: string;
  urgency: string;
  location: string;
  city: string;
  created_at: string;
  assigned_at: string;
  client_name: string;
  budget?: number;
  duration_days: number;
  worker_accepted?: boolean;
}

export default function PendingAssignmentsScreen() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [assignments, setAssignments] = useState<Assignment[]>([]);

  useFocusEffect(
    useCallback(() => {
      loadAssignments();
    }, [])
  );

  const loadAssignments = async () => {
    try {
      setLoading(true);
      const response = await apiService.getPendingAssignments();
      // Handle different response formats and ensure array
      const data = response?.results || response?.data || response || [];
      setAssignments(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Error loading assignments:', error);
      setAssignments([]); // Set empty array on error
      Alert.alert('Error', 'Failed to load pending assignments');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadAssignments();
    setRefreshing(false);
  };

  const getUrgencyColor = (urgency: string) => {
    const colors = {
      low: '#4CAF50',
      medium: '#FFA500',
      high: '#F44336',
      urgent: '#D32F2F',
    };
    return colors[urgency as keyof typeof colors] || theme.textSecondary;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 1) return 'Just now';
    if (hours === 1) return '1 hour ago';
    if (hours < 24) return `${hours} hours ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    return `${days} days ago`;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Pending Assignments" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>
            Loading assignments...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Pending Assignments" showBack />

      {/* Alert Banner */}
      {assignments.length > 0 && (
        <View style={[styles.alertBanner, { backgroundColor: '#FFA500' }]}>
          <Ionicons name="alert-circle" size={24} color="#FFFFFF" />
          <Text style={styles.alertText}>
            {assignments.length} assignment{assignments.length > 1 ? 's' : ''} awaiting response
          </Text>
        </View>
      )}

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {assignments.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="checkmark-done-circle-outline" size={64} color={theme.textSecondary} />
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>
              No pending assignments
            </Text>
            <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>
              You're all caught up! New assignments will appear here.
            </Text>
          </View>
        ) : (
          <View style={styles.assignmentsList}>
            {assignments.map((assignment) => (
              <TouchableOpacity
                key={assignment.id}
                style={[styles.assignmentCard, { backgroundColor: theme.card }]}
                onPress={() => router.push(`/(worker)/assignments/respond/${assignment.id}` as any)}
              >
                {/* Urgency Banner */}
                <View
                  style={[
                    styles.urgencyBanner,
                    { backgroundColor: getUrgencyColor(assignment.urgency) },
                  ]}
                >
                  <Ionicons name="flag" size={16} color="#FFFFFF" />
                  <Text style={styles.urgencyText}>
                    {assignment.urgency.toUpperCase()} PRIORITY
                  </Text>
                </View>

                {/* Title & Category */}
                <Text style={[styles.title, { color: theme.text }]} numberOfLines={2}>
                  {assignment.title}
                </Text>
                <Text style={[styles.category, { color: theme.textSecondary }]}>
                  {assignment.category_name}
                </Text>

                {/* Client Info */}
                <View style={[styles.clientInfo, { backgroundColor: theme.background }]}>
                  <Ionicons name="person-circle-outline" size={20} color={theme.primary} />
                  <Text style={[styles.clientName, { color: theme.text }]}>
                    {assignment.client_name}
                  </Text>
                </View>

                {/* Location */}
                <View style={styles.infoRow}>
                  <Ionicons name="location-outline" size={18} color={theme.textSecondary} />
                  <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                    {assignment.city}
                  </Text>
                </View>

                {/* Duration */}
                <View style={styles.infoRow}>
                  <Ionicons name="calendar-outline" size={18} color={theme.textSecondary} />
                  <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                    {assignment.duration_days} days
                  </Text>
                </View>

                {/* Budget */}
                {assignment.budget && (
                  <View style={styles.infoRow}>
                    <Ionicons name="cash-outline" size={18} color={theme.primary} />
                    <Text style={[styles.budgetText, { color: theme.primary }]}>
                      ${assignment.budget.toFixed(2)}
                    </Text>
                  </View>
                )}

                {/* Time Assigned */}
                <View style={styles.timeRow}>
                  <Ionicons name="time-outline" size={16} color={theme.textSecondary} />
                  <Text style={[styles.timeText, { color: theme.textSecondary }]}>
                    Assigned {formatDate(assignment.assigned_at)}
                  </Text>
                </View>

                {/* Action Button */}
                <TouchableOpacity
                  style={[styles.respondButton, { backgroundColor: theme.primary }]}
                  onPress={() => router.push(`/(worker)/assignments/respond/${assignment.id}` as any)}
                >
                  <Text style={styles.respondButtonText}>Respond Now</Text>
                  <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
                </TouchableOpacity>
              </TouchableOpacity>
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
  alertBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    gap: 8,
  },
  alertText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  content: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
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
  assignmentsList: {
    padding: 16,
  },
  assignmentCard: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  urgencyBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    gap: 6,
  },
  urgencyText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  category: {
    fontSize: 14,
    marginBottom: 12,
  },
  clientInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  clientName: {
    fontSize: 15,
    fontWeight: '600',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  infoText: {
    fontSize: 14,
  },
  budgetText: {
    fontSize: 16,
    fontWeight: '700',
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 12,
    gap: 6,
  },
  timeText: {
    fontSize: 12,
    fontStyle: 'italic',
  },
  respondButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
    borderRadius: 8,
    gap: 8,
  },
  respondButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
