import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useRatingRefresh } from '../../contexts/RatingContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Worker {
  id: number;
  name: string;
  category: string;
  rating: number;
  hourlyRate: number;
  completedJobs: number;
  isAvailable: boolean;
  image?: string;
}

interface Job {
  id: number;
  title: string;
  category: string;
  status: string;
  applicants: number;
  postedDate: string;
}

export default function ClientDashboard() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const { refreshTrigger } = useRatingRefresh();
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [featuredWorkers, setFeaturedWorkers] = useState<Worker[]>([]);
  const [myJobs, setMyJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState({
    activeJobs: 0,
    completedJobs: 0,
    totalSpent: 0,
    favorites: 0,
  });

  // Redirect if wrong user type
  useEffect(() => {
    let mounted = true;
    
    if (user && user.userType !== 'client') {
      console.log('Wrong user type for client dashboard, redirecting to worker');
      router.replace('/(worker)/dashboard');
      return;
    }
    
    // Only load data if user type is correct and component is mounted
    if (user && user.userType === 'client' && mounted) {
      loadDashboardData();
    }
    
    return () => {
      mounted = false;
    };
  }, [user]);

  // Refresh when screen comes into focus (after rating changes)
  useFocusEffect(
    useCallback(() => {
      if (user && user.userType === 'client') {
        loadDashboardData();
      }
    }, [user, refreshTrigger])
  );

  // Additional immediate refresh when rating changes
  useEffect(() => {
    let mounted = true;
    
    if (refreshTrigger > 0 && user && user.userType === 'client' && mounted) {
      loadDashboardData();
    }
    
    return () => {
      mounted = false;
    };
  }, [refreshTrigger, user]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchClientStats(),
        fetchFeaturedWorkers(),
        fetchMyJobs(),
      ]);
    } catch (error) {
      console.error('Error loading dashboard:', error);
      Alert.alert('Error', 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchClientStats = async () => {
    try {
      const data = await apiService.getClientStats();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchFeaturedWorkers = async () => {
    try {
      const data = await apiService.getFeaturedWorkers();
      const workers = data.map((worker: any) => ({
        id: worker.id,
        name: worker.name,
        category: worker.categories?.[0]?.name || 'General',
        rating: worker.average_rating || 0,
        hourlyRate: parseFloat(worker.hourly_rate || '0'),
        completedJobs: worker.completed_jobs || 0,
        isAvailable: worker.availability === 'available',
      }));
      setFeaturedWorkers(workers);
    } catch (error) {
      console.error('Error fetching featured workers:', error);
    }
  };

  const fetchMyJobs = async () => {
    try {
      const data = await apiService.getClientJobs();
      // Handle paginated response
      const jobsList = Array.isArray(data) ? data : (data.results || []);
      const jobs = jobsList
        .filter((job: any) => job.status === 'open' || job.status === 'in_progress')
        .slice(0, 3)
        .map((job: any) => ({
          id: job.id,
          title: job.title,
          category: job.category_name || 'General',
          status: job.status === 'open' ? 'active' : job.status,
          applicants: job.application_count || 0,
          postedDate: new Date(job.created_at).toLocaleDateString(),
        }));
      setMyJobs(jobs);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const handleSearch = () => {
    if (!searchQuery.trim()) {
      Alert.alert('Search', 'Please enter a search term');
      return;
    }
    router.push(`/(client)/search?q=${searchQuery}`);
  };

  const handleRequestWorker = (workerId: number) => {
    router.push(`/(client)/request-worker/${workerId}` as any);
  };

  const handleViewWorkerProfile = (workerId: number) => {
    router.push(`/(client)/worker/${workerId}`);
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header 
        title={`Hello, ${user?.firstName || 'Client'}!`}
        showNotifications={true}
        onNotificationPress={() => router.push('/(client)/notifications' as any)}
      />

      {loading && !refreshing ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading dashboard...</Text>
        </View>
      ) : (
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.primary]} />
        }
      >
        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <TextInput
            style={[styles.searchInput, { backgroundColor: theme.card, color: theme.text, fontFamily: 'Poppins_400Regular' }]}
            placeholder="Search for workers or services..."
            placeholderTextColor={theme.textSecondary}
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={handleSearch}
          />
          <TouchableOpacity style={[styles.searchButton, { backgroundColor: theme.primary }]} onPress={handleSearch}>
            <Ionicons name="search" size={20} color={theme.textLight} />
          </TouchableOpacity>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          <View style={[styles.statCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>{stats.activeJobs}</Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Active Jobs</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>{stats.completedJobs}</Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Completed</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>SDG {((Number(stats.totalSpent) || 0) / 1000).toFixed(1)}K</Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Total Spent</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>{stats.favorites}</Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Favorites</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>Quick Actions</Text>
          <View style={styles.quickActions}>
            <TouchableOpacity
              style={[styles.actionCard, { backgroundColor: theme.card }]}
              onPress={() => router.push('/(client)/post-job' as any)}
            >
              <Ionicons name="create-outline" size={36} color={theme.primary} />
              <Text style={[styles.actionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Post a Job</Text>
              <Text style={[styles.actionSubtitle, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Get multiple bids</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionCard, { backgroundColor: theme.card }]}
              onPress={() => router.push('/(client)/search')}
            >
              <Ionicons name="search-outline" size={36} color={theme.primary} />
              <Text style={[styles.actionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Find Workers</Text>
              <Text style={[styles.actionSubtitle, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Browse & hire now</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Featured Available Workers */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>Available Workers</Text>
            <TouchableOpacity onPress={() => router.push('/(client)/search')}>
              <Text style={[styles.seeAllText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>See All</Text>
            </TouchableOpacity>
          </View>

          {featuredWorkers.map((worker) => (
            <View key={worker.id} style={[styles.workerCard, { backgroundColor: theme.card }]}>
              <View style={styles.workerInfo}>
                <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
                  <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                    {worker.name.split(' ').map(n => n[0]).join('')}
                  </Text>
                </View>
                <View style={styles.workerDetails}>
                  <View style={styles.workerNameRow}>
                    <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{worker.name}</Text>
                    {worker.isAvailable && (
                      <View style={styles.availableBadge}>
                        <Text style={[styles.availableBadgeText, { fontFamily: 'Poppins_600SemiBold' }]}>Available</Text>
                      </View>
                    )}
                  </View>
                  <Text style={[styles.workerCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{worker.category}</Text>
                  <View style={styles.workerStats}>
                    <Ionicons name="star" size={13} color="#F59E0B" />
                    <Text style={[styles.workerRating, { fontFamily: 'Poppins_600SemiBold' }]}> {worker.rating}</Text>
                    <Text style={[styles.workerJobs, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>• {worker.completedJobs} jobs</Text>
                    <Text style={[styles.workerRate, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>• SDG {worker.hourlyRate}/hr</Text>
                  </View>
                </View>
              </View>

              <View style={styles.workerActions}>
                <TouchableOpacity
                  style={[styles.viewProfileButton, { backgroundColor: theme.background, borderColor: theme.border }]}
                  onPress={() => handleViewWorkerProfile(worker.id)}
                >
                  <Text style={[styles.viewProfileButtonText, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>View Profile</Text>
                </TouchableOpacity>
                {worker.isAvailable && (
                  <TouchableOpacity
                    style={[styles.requestButton, { backgroundColor: theme.primary }]}
                    onPress={() => handleRequestWorker(worker.id)}
                  >
                    <Text style={[styles.requestButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Request Now</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          ))}
        </View>

        {/* My Jobs */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>My Jobs</Text>
            <TouchableOpacity onPress={() => router.push('/(client)/jobs')}>
              <Text style={[styles.seeAllText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>See All</Text>
            </TouchableOpacity>
          </View>

          {myJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={[styles.jobCard, { backgroundColor: theme.card }]}
              onPress={() => router.push(`/(client)/job/${job.id}` as any)}
            >
              <View style={styles.jobHeader}>
                <Text style={[styles.jobTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{job.title}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    job.status === 'active' && styles.statusBadgeActive,
                    job.status === 'in_progress' && styles.statusBadgeInProgress,
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      { fontFamily: 'Poppins_600SemiBold' },
                      job.status === 'active' && styles.statusTextActive,
                      job.status === 'in_progress' && styles.statusTextInProgress,
                    ]}
                  >
                    {job.status === 'active' ? 'Active' : 'In Progress'}
                  </Text>
                </View>
              </View>
              <Text style={[styles.jobCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{job.category}</Text>
              <View style={styles.jobFooter}>
                <Text style={[styles.jobInfo, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  {job.applicants} applicant{job.applicants !== 1 ? 's' : ''}
                </Text>
                <Text style={[styles.jobInfo, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>• {job.postedDate}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Categories */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>Browse by Category</Text>
          <View style={styles.categoriesGrid}>
            {[
              { name: 'Plumbing', icon: 'hammer-outline' },
              { name: 'Electrical', icon: 'flash-outline' },
              { name: 'Carpentry', icon: 'construct-outline' },
              { name: 'Cleaning', icon: 'sparkles-outline' },
              { name: 'Painting', icon: 'color-palette-outline' },
              { name: 'Moving', icon: 'cube-outline' },
            ].map(
              (category) => (
                <TouchableOpacity
                  key={category.name}
                  style={[styles.categoryCard, { backgroundColor: theme.card }]}
                  onPress={() => router.push(`/(client)/search?category=${category.name}`)}
                >
                  <Ionicons name={category.icon as any} size={32} color={theme.primary} />
                  <Text style={[styles.categoryName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>{category.name}</Text>
                </TouchableOpacity>
              )
            )}
          </View>
        </View>
      </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  searchContainer: {
    flexDirection: 'row',
    marginBottom: 20,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    height: 50,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  searchButton: {
    width: 50,
    height: 50,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    minWidth: '22%',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statValue: {
    fontSize: 18,
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 10,
    textAlign: 'center',
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
  },
  seeAllText: {
    fontSize: 14,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionCard: {
    flex: 1,
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  actionTitle: {
    fontSize: 15,
    marginBottom: 4,
    marginTop: 8,
  },
  actionSubtitle: {
    fontSize: 12,
  },
  workerCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  workerInfo: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  workerAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  workerAvatarText: {
    fontSize: 20,
  },
  workerDetails: {
    flex: 1,
  },
  workerNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  workerName: {
    fontSize: 16,
    marginRight: 8,
  },
  availableBadge: {
    backgroundColor: '#D1FAE5',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  availableBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#065F46',
  },
  workerCategory: {
    fontSize: 14,
    marginBottom: 4,
  },
  workerStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  workerRating: {
    fontSize: 13,
    color: '#F59E0B',
  },
  workerJobs: {
    fontSize: 13,
    marginLeft: 4,
  },
  workerRate: {
    fontSize: 13,
    marginLeft: 4,
  },
  workerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  viewProfileButton: {
    flex: 1,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  viewProfileButtonText: {
    fontSize: 13,
  },
  requestButton: {
    flex: 1,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  requestButtonText: {
    fontSize: 13,
  },
  jobCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  jobTitle: {
    flex: 1,
    fontSize: 15,
    marginRight: 8,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusBadgeActive: {
    backgroundColor: '#DBEAFE',
  },
  statusBadgeInProgress: {
    backgroundColor: '#FEF3C7',
  },
  statusText: {
    fontSize: 11,
  },
  statusTextActive: {
    color: '#1E40AF',
  },
  statusTextInProgress: {
    color: '#92400E',
  },
  jobCategory: {
    fontSize: 13,
    marginBottom: 8,
  },
  jobFooter: {
    flexDirection: 'row',
  },
  jobInfo: {
    fontSize: 12,
    marginRight: 4,
  },
  categoriesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  categoryCard: {
    width: '30%',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  categoryName: {
    fontSize: 12,
    textAlign: 'center',
    marginTop: 8,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
});
