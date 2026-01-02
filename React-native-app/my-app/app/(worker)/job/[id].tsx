import React, { useState, useEffect, useCallback } from 'react';
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
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import { useRatingRefresh } from '../../../contexts/RatingContext';
import Header from '../../../components/Header';
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
  const { theme, isDark } = useTheme();
  const { refreshTrigger } = useRatingRefresh();
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [applying, setApplying] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [savingJob, setSavingJob] = useState(false);

  useEffect(() => {
    loadJobDetail();
    checkIfSaved();
  }, [id]);

  // Refresh when screen comes into focus (after rating changes)
  useFocusEffect(
    useCallback(() => {
      loadJobDetail();
      checkIfSaved();
    }, [id, refreshTrigger])
  );

  const loadJobDetail = async () => {
    try {
      setLoading(true);
      // Fetch real job data from API
      const jobData = await apiService.getJobDetail(Number(id));
      setJob(jobData);
    } catch (error) {
      console.error('Error loading job:', error);
      Alert.alert('Error', 'Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const checkIfSaved = async () => {
    try {
      const response = await apiService.isJobSaved(Number(id));
      setIsSaved(response.is_saved);
    } catch (error) {
      console.error('Error checking saved status:', error);
    }
  };

  const handleToggleSaveJob = async () => {
    try {
      setSavingJob(true);
      
      if (isSaved) {
        await apiService.unsaveJob(Number(id));
        setIsSaved(false);
      } else {
        await apiService.saveJob(Number(id));
        setIsSaved(true);
      }
    } catch (error) {
      console.error('Error toggling saved job:', error);
      Alert.alert('Error', 'Failed to update saved status');
    } finally {
      setSavingJob(false);
    }
  };

  const handleApply = () => {
    router.push(`/job/${id}/apply` as any);
  };

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    loadingText: {
      marginTop: 12,
      fontSize: 16,
      color: theme.textSecondary,
      fontFamily: 'Poppins_400Regular',
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 40,
    },
    emptyText: {
      fontSize: 18,
      color: theme.textSecondary,
      fontFamily: 'Poppins_400Regular',
      marginTop: 16,
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
      color: theme.text,
      marginBottom: 12,
      fontFamily: 'Poppins_700Bold',
    },
    categoryBadge: {
      backgroundColor: isDark ? theme.primaryDark : '#E0F2FE',
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 8,
      alignSelf: 'flex-start',
    },
    categoryText: {
      fontSize: 14,
      color: theme.primary,
      fontFamily: 'Poppins_600SemiBold',
    },
    budgetCard: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 20,
      alignItems: 'center',
      marginBottom: 20,
      ...(isDark ? {} : {
        elevation: 3,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
      }),
    },
    budgetLabel: {
      fontSize: 14,
      color: theme.textSecondary,
      marginBottom: 4,
      fontFamily: 'Poppins_400Regular',
    },
    budgetAmount: {
      fontSize: 32,
      color: theme.primary,
      marginBottom: 4,
      fontFamily: 'Poppins_700Bold',
    },
    budgetDuration: {
      fontSize: 14,
      color: theme.textSecondary,
      fontFamily: 'Poppins_400Regular',
    },
    infoSection: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      marginBottom: 20,
      ...(isDark ? {} : {
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
      }),
    },
    infoItem: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: theme.border,
    },
    infoTextContainer: {
      flex: 1,
    },
    infoLabel: {
      fontSize: 12,
      color: theme.textSecondary,
      marginBottom: 2,
      fontFamily: 'Poppins_400Regular',
    },
    infoValue: {
      fontSize: 16,
      color: theme.text,
      fontFamily: 'Poppins_600SemiBold',
    },
    descriptionSection: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      marginBottom: 20,
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      ...(isDark ? {} : {
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
      }),
    },
    saveButton: {
      width: 48,
      height: 48,
      borderRadius: 24,
      backgroundColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)',
      justifyContent: 'center',
      alignItems: 'center',
    },
    sectionTitle: {
      fontSize: 18,
      color: theme.text,
      marginBottom: 12,
      fontFamily: 'Poppins_700Bold',
    },
    descriptionText: {
      fontSize: 15,
      color: theme.textSecondary,
      lineHeight: 24,
      fontFamily: 'Poppins_400Regular',
    },
    requirementsSection: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      ...(isDark ? {} : {
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
      }),
    },
    requirementItem: {
      flexDirection: 'row',
      marginBottom: 8,
    },
    requirementBullet: {
      fontSize: 16,
      color: theme.primary,
      marginRight: 8,
      fontFamily: 'Poppins_700Bold',
    },
    requirementText: {
      flex: 1,
      fontSize: 15,
      color: theme.textSecondary,
      lineHeight: 22,
      fontFamily: 'Poppins_400Regular',
    },
    bottomSection: {
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: theme.surface,
      padding: 20,
      borderTopWidth: 1,
      borderTopColor: theme.border,
      ...(isDark ? {} : {
        elevation: 8,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
      }),
    },
    applyButton: {
      backgroundColor: theme.primary,
      borderRadius: 12,
      padding: 16,
      alignItems: 'center',
      flexDirection: 'row',
      justifyContent: 'center',
    },
    applyButtonDisabled: {
      opacity: 0.6,
    },
    applyButtonText: {
      color: '#FFFFFF',
      fontSize: 18,
      fontFamily: 'Poppins_700Bold',
    },
  });

  if (loading) {
    return (
      <View style={styles.container}>
        <StatusBar style={isDark ? 'light' : 'dark'} />
        <Header title="Job Details" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={styles.loadingText}>Loading job...</Text>
        </View>
      </View>
    );
  }

  if (!job) {
    return (
      <View style={styles.container}>
        <StatusBar style={isDark ? 'light' : 'dark'} />
        <Header title="Job Details" showBack />
        <View style={styles.emptyContainer}>
          <Ionicons name="document-text-outline" size={64} color={theme.textSecondary} />
          <Text style={styles.emptyText}>Job not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      
      <Header title="Job Details" showBack />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Job Title with Save Button */}
        <View style={styles.titleSection}>
          <View style={{ flex: 1, paddingRight: 16 }}>
            <Text style={styles.jobTitle}>{job.title}</Text>
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>{job.category}</Text>
            </View>
          </View>
          
          {/* Save Button */}
          <TouchableOpacity
            style={styles.saveButton}
            onPress={handleToggleSaveJob}
            disabled={savingJob}
          >
            <Ionicons 
              name={isSaved ? "heart" : "heart-outline"} 
              size={28} 
              color={isSaved ? "#EF4444" : theme.textSecondary} 
            />
          </TouchableOpacity>
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
            <Ionicons name="location-outline" size={24} color={theme.primary} style={{ marginRight: 12, width: 32 }} />
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Location</Text>
              <Text style={styles.infoValue}>{job.location}</Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Ionicons name="person-outline" size={24} color={theme.primary} style={{ marginRight: 12, width: 32 }} />
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Client</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <Text style={styles.infoValue}>{job.client.name}</Text>
                <Ionicons name="star" size={16} color="#FFA500" style={{ marginLeft: 6, marginRight: 4 }} />
                <Text style={styles.infoValue}>{job.client.rating}</Text>
              </View>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Ionicons name="calendar-outline" size={24} color={theme.primary} style={{ marginRight: 12, width: 32 }} />
            <View style={styles.infoTextContainer}>
              <Text style={styles.infoLabel}>Posted</Text>
              <Text style={styles.infoValue}>{job.postedDate}</Text>
            </View>
          </View>

          <View style={styles.infoItem}>
            <Ionicons name="people-outline" size={24} color={theme.primary} style={{ marginRight: 12, width: 32 }} />
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
          <Ionicons 
            name={applying ? 'hourglass-outline' : 'checkmark-circle'} 
            size={20} 
            color="#FFFFFF" 
            style={{ marginRight: 8 }}
          />
          <Text style={styles.applyButtonText}>
            {applying ? 'Applying...' : 'Apply for this Job'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}