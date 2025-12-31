import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import { useRatingRefresh } from '../../../contexts/RatingContext';
import apiService from '../../../services/api';

interface JobDetail {
  id: number;
  title: string;
  description: string;
  category: string;
  budget: number;
  location: string;
  status: string;
  created_at: string;
  worker?: {
    id: number;
    name: string;
    rating: number;
  };
  applications_count: number;
}

export default function JobDetailScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const { refreshTrigger } = useRatingRefresh();
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState<JobDetail | null>(null);

  useEffect(() => {
    loadJobDetail();
  }, [id]);

  // Refresh when screen comes into focus (after rating changes)
  useFocusEffect(
    useCallback(() => {
      loadJobDetail();
    }, [id, refreshTrigger])
  );

  const loadJobDetail = async () => {
    try {
      setLoading(true);
      const jobData = await apiService.getJobDetail(Number(id));
      setJob(jobData);
    } catch (error) {
      console.error('Error loading job:', error);
      Alert.alert('Error', 'Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return '#3B82F6';
      case 'in_progress':
        return '#F59E0B';
      case 'completed':
        return '#10B981';
      case 'cancelled':
        return '#EF4444';
      default:
        return theme.textSecondary;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'open':
        return 'Open';
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.textLight} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Job Details</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Loading job...</Text>
        </View>
      </View>
    );
  }

  if (!job) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.textLight} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Job Details</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.emptyContainer}>
          <Ionicons name="briefcase-outline" size={64} color={theme.textSecondary} />
          <Text style={[styles.emptyText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Job not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.primary }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.textLight} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Job Details</Text>
        <View style={styles.headerRight} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Job Info Card */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.titleRow}>
            <Text style={[styles.jobTitle, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>{job.title}</Text>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(job.status) + '20' }]}>
              <Text style={[styles.statusText, { color: getStatusColor(job.status), fontFamily: 'Poppins_600SemiBold' }]}>
                {getStatusLabel(job.status)}
              </Text>
            </View>
          </View>

          <View style={[styles.infoRow, { borderTopColor: theme.border }]}>
            <Ionicons name="pricetag" size={20} color={theme.primary} />
            <Text style={[styles.infoText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              {job.category}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="location" size={20} color={theme.primary} />
            <Text style={[styles.infoText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              {job.location}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="cash" size={20} color={theme.primary} />
            <Text style={[styles.budgetText, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>
              SDG {job.budget}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="people" size={20} color={theme.primary} />
            <Text style={[styles.infoText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              {job.applications_count} Applications
            </Text>
          </View>
        </View>

        {/* Description */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Description</Text>
          <Text style={[styles.description, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
            {job.description}
          </Text>
        </View>

        {/* Worker Info (if assigned) */}
        {job.worker && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Assigned Worker</Text>
            <TouchableOpacity
              style={styles.workerCard}
              onPress={() => router.push(`/(client)/worker/${job.worker?.id}` as any)}
            >
              {job.worker?.profile_image ? (
                <Image source={{ uri: job.worker.profile_image }} style={[styles.workerAvatar, { borderRadius: 24 }]} />
              ) : (
                <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
                  <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                    {job.worker?.name?.[0] || ''}
                  </Text>
                </View>
              )}
              <View style={styles.workerInfo}>
                <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                  {job.worker.name}
                </Text>
                <View style={styles.ratingRow}>
                  <Ionicons name="star" size={16} color="#FCD34D" />
                    <Text style={[styles.ratingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                      {(Number(job.worker?.rating) || 0).toFixed(1)}
                    </Text>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={24} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Action Buttons (if job is open) */}
      {job.status === 'open' && (
        <View style={[styles.bottomSection, { backgroundColor: theme.card, borderTopColor: theme.border }]}>
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: theme.primary }]}
            onPress={() => router.push(`/(client)/job/${id}/applications` as any)}
          >
            <Ionicons name="people" size={20} color={theme.textLight} />
            <Text style={[styles.actionButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>
              View Applications
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  headerTitle: {
    fontSize: 20,
  },
  headerRight: {
    width: 40,
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
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 18,
    marginTop: 16,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  card: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  jobTitle: {
    fontSize: 22,
    flex: 1,
    marginRight: 12,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
  },
  infoText: {
    fontSize: 15,
  },
  budgetText: {
    fontSize: 18,
  },
  sectionTitle: {
    fontSize: 18,
    marginBottom: 12,
  },
  description: {
    fontSize: 15,
    lineHeight: 24,
  },
  workerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  workerAvatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  workerAvatarText: {
    fontSize: 20,
  },
  workerInfo: {
    flex: 1,
  },
  workerName: {
    fontSize: 16,
    marginBottom: 4,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  ratingText: {
    fontSize: 14,
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    borderTopWidth: 1,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 12,
    padding: 16,
  },
  actionButtonText: {
    fontSize: 16,
  },
});
