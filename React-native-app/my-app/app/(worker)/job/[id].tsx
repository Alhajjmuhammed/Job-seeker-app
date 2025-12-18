import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import apiService from '../../../services/api';

interface JobDetail {
  id: number;
  title: string;
  description: string;
  category: string;
  client: {
    name: string;
    rating: number;
  };
  budget: number;
  location: string;
  duration: string;
  postedDate: string;
  applicants: number;
  status: string;
}

export default function JobDetailScreen() {
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    loadJobDetail();
  }, [id]);

  const loadJobDetail = async () => {
    try {
      setLoading(true);
      // TODO: Implement getJobDetail API endpoint
      // const jobData = await apiService.getJobDetail(Number(id));
      // setJob(jobData);
      
      // Mock data for now
      setJob({
        id: Number(id),
        title: 'Fix Kitchen Sink Leak',
        description: 'Need an experienced plumber to fix a leaking kitchen sink. The leak is under the sink and seems to be coming from the pipe connections. Work should be completed within 2-3 hours.',
        category: 'Plumbing',
        client: {
          name: 'Ahmed Hassan',
          rating: 4.8,
        },
        budget: 500,
        location: 'Khartoum, Sudan',
        duration: '2-3 hours',
        postedDate: '2 hours ago',
        applicants: 3,
        status: 'open',
      });
    } catch (error) {
      console.error('Error loading job:', error);
      Alert.alert('Error', 'Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    Alert.alert(
      'Apply for Job',
      'Would you like to apply for this job?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Apply',
          onPress: async () => {
            try {
              setApplying(true);
              await apiService.applyForJob(Number(id));
              Alert.alert('Success', 'Application submitted successfully!');
              router.back();
            } catch (error: any) {
              Alert.alert('Error', error.message || 'Failed to apply for job');
            } finally {
              setApplying(false);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Text style={styles.backIcon}>←</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Job Details</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0F766E" />
          <Text style={styles.loadingText}>Loading job...</Text>
        </View>
      </View>
    );
  }

  if (!job) {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Text style={styles.backIcon}>←</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Job Details</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyText}>Job not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Job Details</Text>
        <View style={styles.headerRight} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Job Title */}
        <View style={styles.titleSection}>
          <Text style={styles.jobTitle}>{job.title}</Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{job.category}</Text>
          </View>
        </View>

        {/* Budget Card */}
        <View style={styles.budgetCard}>
          <Text style={styles.budgetLabel}>Budget</Text>
          <Text style={styles.budgetAmount}>SDG {job.budget}</Text>
          <Text style={styles.budgetDuration}>{job.duration}</Text>
        </View>

        {/* Job Info */}
        <View style={styles.infoSection}>
          <View style={styles.infoItem}>
            <Text style={styles.infoIcon}>📍</Text>
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Location</Text>
              <Text style={styles.infoValue}>{job.location}</Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Text style={styles.infoIcon}>👤</Text>
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Client</Text>
              <Text style={styles.infoValue}>
                {job.client.name} ⭐ {job.client.rating}
              </Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Text style={styles.infoIcon}>📅</Text>
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Posted</Text>
              <Text style={styles.infoValue}>{job.postedDate}</Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Text style={styles.infoIcon}>👥</Text>
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Applicants</Text>
              <Text style={styles.infoValue}>{job.applicants} workers applied</Text>
            </View>
          </View>
        </View>

        {/* Description */}
        <View style={styles.descriptionSection}>
          <Text style={styles.sectionTitle}>Job Description</Text>
          <Text style={styles.descriptionText}>{job.description}</Text>
        </View>

        {/* Requirements */}
        <View style={styles.requirementsSection}>
          <Text style={styles.sectionTitle}>Requirements</Text>
          <View style={styles.requirementItem}>
            <Text style={styles.requirementBullet}>•</Text>
            <Text style={styles.requirementText}>Professional experience in {job.category}</Text>
          </View>
          <View style={styles.requirementItem}>
            <Text style={styles.requirementBullet}>•</Text>
            <Text style={styles.requirementText}>Own tools and equipment</Text>
          </View>
          <View style={styles.requirementItem}>
            <Text style={styles.requirementBullet}>•</Text>
            <Text style={styles.requirementText}>Good communication skills</Text>
          </View>
        </View>
      </ScrollView>

      {/* Apply Button */}
      <View style={styles.bottomSection}>
        <TouchableOpacity
          style={[styles.applyButton, applying && styles.applyButtonDisabled]}
          onPress={handleApply}
          disabled={applying}
        >
          <Text style={styles.applyButtonText}>
            {applying ? 'Applying...' : '✓ Apply for this Job'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
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
  backIcon: {
    fontSize: 28,
    color: '#FFFFFF',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
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
    color: '#6B7280',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 18,
    color: '#6B7280',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  titleSection: {
    marginBottom: 20,
  },
  jobTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  categoryBadge: {
    backgroundColor: '#E0F2FE',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  categoryText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0369A1',
  },
  budgetCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 20,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  budgetLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 4,
  },
  budgetAmount: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#0F766E',
    marginBottom: 4,
  },
  budgetDuration: {
    fontSize: 14,
    color: '#6B7280',
  },
  infoSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  infoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  infoIcon: {
    fontSize: 24,
    marginRight: 12,
    width: 32,
  },
  infoTextContainer: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  descriptionSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  descriptionText: {
    fontSize: 15,
    color: '#4B5563',
    lineHeight: 24,
  },
  requirementsSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  requirementItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  requirementBullet: {
    fontSize: 16,
    color: '#0F766E',
    marginRight: 8,
    fontWeight: 'bold',
  },
  requirementText: {
    flex: 1,
    fontSize: 15,
    color: '#4B5563',
    lineHeight: 22,
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#FFFFFF',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  applyButton: {
    backgroundColor: '#0F766E',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  applyButtonDisabled: {
    opacity: 0.6,
  },
  applyButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
