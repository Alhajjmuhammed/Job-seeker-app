import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface SavedJob {
  saved_id: number;
  saved_at: string;
  job: {
    id: number;
    title: string;
    description: string;
    status: string;
    category_name?: string;
    client_name: string;
    location?: string;
    budget?: string;
    created_at: string;
  };
  is_available: boolean;
}

export default function SavedJobsScreen() {
  const { theme, isDark } = useTheme();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);

  // Check if professional worker
  const isProfessional = user?.workerType === 'professional';

  useEffect(() => {
    if (!isProfessional) {
      router.replace('/jobs');
      return;
    }
    loadSavedJobs();
  }, []);

  const loadSavedJobs = async () => {
    try {
      setLoading(true);
      const response = await apiService.getSavedJobs();
      setSavedJobs(response.saved_jobs || []);
    } catch (error) {
      console.error('Error loading saved jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadSavedJobs();
    setRefreshing(false);
  };

  const handleUnsaveJob = async (jobId: number) => {
    try {
      await apiService.unsaveJob(jobId);
      setSavedJobs(prev => prev.filter(s => s.job.id !== jobId));
    } catch (error) {
      console.error('Error unsaving job:', error);
    }
  };

  const confirmUnsave = (jobId: number, title: string) => {
    Alert.alert(
      'Remove Saved Job',
      `Remove "${title}" from saved jobs?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Remove', 
          style: 'destructive',
          onPress: () => handleUnsaveJob(jobId)
        },
      ]
    );
  };

  const renderSavedJobCard = (saved: SavedJob) => {
    const { job, is_available } = saved;
    
    return (
      <View
        key={saved.saved_id}
        style={[
          styles.jobCard, 
          { 
            backgroundColor: theme.surface, 
            shadowColor: isDark ? '#000' : '#000', 
            shadowOpacity: isDark ? 0.3 : 0.1,
            opacity: is_available ? 1 : 0.6,
          }
        ]}
      >
        <TouchableOpacity
          style={styles.jobCardContent}
          onPress={() => router.push(`/job/${job.id}` as any)}
          disabled={!is_available}
        >
          <View style={styles.jobHeader}>
            <View style={{ flex: 1, paddingRight: 8 }}>
              <Text style={[styles.jobTitle, { color: theme.text }]} numberOfLines={2}>
                {job.title}
              </Text>
              {job.category_name && (
                <View style={[styles.categoryBadge, { backgroundColor: isDark ? 'rgba(15, 118, 110, 0.2)' : '#F0FDF4' }]}>
                  <Text style={[styles.categoryText, { color: theme.primary }]}>{job.category_name}</Text>
                </View>
              )}
            </View>
          </View>

          {!is_available && (
            <View style={[styles.unavailableBadge, { backgroundColor: 'rgba(239, 68, 68, 0.1)' }]}>
              <Ionicons name="close-circle" size={16} color="#EF4444" />
              <Text style={[styles.unavailableText, { color: '#EF4444' }]}>No longer available</Text>
            </View>
          )}

          <Text style={[styles.jobDescription, { color: theme.textSecondary }]} numberOfLines={2}>
            {job.description}
          </Text>

          <View style={styles.jobMeta}>
            <View style={styles.metaItem}>
              <Ionicons name="business-outline" size={16} color={theme.textSecondary} />
              <Text style={[styles.metaText, { color: theme.textSecondary }]}>{job.client_name}</Text>
            </View>
            
            {job.location && (
              <View style={styles.metaItem}>
                <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
                <Text style={[styles.metaText, { color: theme.textSecondary }]}>{job.location}</Text>
              </View>
            )}
          </View>

          {job.budget && (
            <View style={styles.budgetRow}>
              <Text style={[styles.budgetLabel, { color: theme.textSecondary }]}>Budget:</Text>
              <Text style={[styles.budgetAmount, { color: theme.primary }]}>${job.budget}</Text>
            </View>
          )}

          <View style={styles.savedInfo}>
            <Ionicons name="time-outline" size={14} color={theme.textSecondary} />
            <Text style={[styles.savedDate, { color: theme.textSecondary }]}>
              Saved {new Date(saved.saved_at).toLocaleDateString()}
            </Text>
          </View>
        </TouchableOpacity>
        
        {/* Unsave Button */}
        <TouchableOpacity
          style={styles.unsaveButton}
          onPress={() => confirmUnsave(job.id, job.title)}
        >
          <Ionicons 
            name="heart" 
            size={24} 
            color="#EF4444" 
          />
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <View style={styles.content}>
        <View style={styles.titleContainer}>
          <Ionicons name="heart" size={28} color={theme.primary} />
          <Text style={[styles.title, { color: theme.text }]}>Saved Jobs</Text>
        </View>

        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading saved jobs...</Text>
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
            {savedJobs.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="heart-outline" size={56} color={theme.textSecondary} style={{ marginBottom: 16 }} />
                <Text style={[styles.emptyTitle, { color: theme.text }]}>No Saved Jobs</Text>
                <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
                  Save jobs to view them later
                </Text>
                <TouchableOpacity
                  style={[styles.browseButton, { backgroundColor: theme.primary }]}
                  onPress={() => router.push('/browse-jobs' as any)}
                >
                  <Text style={styles.browseButtonText}>Browse Jobs</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                <Text style={[styles.resultCount, { color: theme.textSecondary }]}>
                  {savedJobs.length} saved {savedJobs.length === 1 ? 'job' : 'jobs'}
                </Text>
                {savedJobs.map(renderSavedJobCard)}
              </>
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
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
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
  resultCount: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 16,
  },
  jobCard: {
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    position: 'relative',
  },
  jobCardContent: {
    padding: 20,
  },
  unsaveButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  jobHeader: {
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  jobTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 8,
  },
  categoryBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  categoryText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  unavailableBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  unavailableText: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  jobDescription: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 12,
    lineHeight: 20,
  },
  jobMeta: {
    gap: 8,
    marginBottom: 12,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  budgetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  budgetLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  budgetAmount: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  savedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  savedDate: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
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
    marginBottom: 24,
  },
  browseButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  browseButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
});
