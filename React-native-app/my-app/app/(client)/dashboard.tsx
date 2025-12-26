import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Image,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
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

  useEffect(() => {
    loadDashboardData();
  }, []);

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
      const jobs = data
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
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Hello! 👋</Text>
          <Text style={styles.name}>{user?.firstName} {user?.lastName}</Text>
        </View>
        <TouchableOpacity style={styles.notificationButton}>
          <Text style={styles.notificationText}>🔔</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>3</Text>
          </View>
        </TouchableOpacity>
      </View>

      {loading && !refreshing ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0F766E" />
          <Text style={styles.loadingText}>Loading dashboard...</Text>
        </View>
      ) : (
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search for workers or services..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={handleSearch}
          />
          <TouchableOpacity style={styles.searchButton} onPress={handleSearch}>
            <Text style={styles.searchButtonText}>🔍</Text>
          </TouchableOpacity>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.activeJobs}</Text>
            <Text style={styles.statLabel}>Active Jobs</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.completedJobs}</Text>
            <Text style={styles.statLabel}>Completed</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>SDG {(stats.totalSpent / 1000).toFixed(1)}K</Text>
            <Text style={styles.statLabel}>Total Spent</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.favorites}</Text>
            <Text style={styles.statLabel}>Favorites</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.quickActions}>
            <TouchableOpacity
              style={styles.actionCard}
              onPress={() => router.push('/(client)/post-job' as any)}
            >
              <Text style={styles.actionIcon}>📝</Text>
              <Text style={styles.actionTitle}>Post a Job</Text>
              <Text style={styles.actionSubtitle}>Get multiple bids</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionCard}
              onPress={() => router.push('/(client)/search')}
            >
              <Text style={styles.actionIcon}>🔍</Text>
              <Text style={styles.actionTitle}>Find Workers</Text>
              <Text style={styles.actionSubtitle}>Browse & hire now</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Featured Available Workers */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Available Workers</Text>
            <TouchableOpacity onPress={() => router.push('/(client)/search')}>
              <Text style={styles.seeAllText}>See All</Text>
            </TouchableOpacity>
          </View>

          {featuredWorkers.map((worker) => (
            <View key={worker.id} style={styles.workerCard}>
              <View style={styles.workerInfo}>
                <View style={styles.workerAvatar}>
                  <Text style={styles.workerAvatarText}>
                    {worker.name.split(' ').map(n => n[0]).join('')}
                  </Text>
                </View>
                <View style={styles.workerDetails}>
                  <View style={styles.workerNameRow}>
                    <Text style={styles.workerName}>{worker.name}</Text>
                    {worker.isAvailable && (
                      <View style={styles.availableBadge}>
                        <Text style={styles.availableBadgeText}>Available</Text>
                      </View>
                    )}
                  </View>
                  <Text style={styles.workerCategory}>{worker.category}</Text>
                  <View style={styles.workerStats}>
                    <Text style={styles.workerRating}>⭐ {worker.rating}</Text>
                    <Text style={styles.workerJobs}>• {worker.completedJobs} jobs</Text>
                    <Text style={styles.workerRate}>• SDG {worker.hourlyRate}/hr</Text>
                  </View>
                </View>
              </View>

              <View style={styles.workerActions}>
                <TouchableOpacity
                  style={styles.viewProfileButton}
                  onPress={() => handleViewWorkerProfile(worker.id)}
                >
                  <Text style={styles.viewProfileButtonText}>View Profile</Text>
                </TouchableOpacity>
                {worker.isAvailable && (
                  <TouchableOpacity
                    style={styles.requestButton}
                    onPress={() => handleRequestWorker(worker.id)}
                  >
                    <Text style={styles.requestButtonText}>Request Now</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          ))}
        </View>

        {/* My Jobs */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>My Jobs</Text>
            <TouchableOpacity onPress={() => router.push('/(client)/jobs')}>
              <Text style={styles.seeAllText}>See All</Text>
            </TouchableOpacity>
          </View>

          {myJobs.map((job) => (
            <TouchableOpacity
              key={job.id}
              style={styles.jobCard}
              onPress={() => router.push(`/(client)/job/${job.id}` as any)}
            >
              <View style={styles.jobHeader}>
                <Text style={styles.jobTitle}>{job.title}</Text>
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
                      job.status === 'active' && styles.statusTextActive,
                      job.status === 'in_progress' && styles.statusTextInProgress,
                    ]}
                  >
                    {job.status === 'active' ? 'Active' : 'In Progress'}
                  </Text>
                </View>
              </View>
              <Text style={styles.jobCategory}>{job.category}</Text>
              <View style={styles.jobFooter}>
                <Text style={styles.jobInfo}>
                  {job.applicants} applicant{job.applicants !== 1 ? 's' : ''}
                </Text>
                <Text style={styles.jobInfo}>• {job.postedDate}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Categories */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Browse by Category</Text>
          <View style={styles.categoriesGrid}>
            {['Plumbing', 'Electrical', 'Carpentry', 'Cleaning', 'Painting', 'Moving'].map(
              (category) => (
                <TouchableOpacity
                  key={category}
                  style={styles.categoryCard}
                  onPress={() => router.push(`/(client)/search?category=${category}`)}
                >
                  <Text style={styles.categoryIcon}>
                    {category === 'Plumbing'
                      ? '🔧'
                      : category === 'Electrical'
                      ? '⚡'
                      : category === 'Carpentry'
                      ? '🪚'
                      : category === 'Cleaning'
                      ? '🧹'
                      : category === 'Painting'
                      ? '🎨'
                      : '📦'}
                  </Text>
                  <Text style={styles.categoryName}>{category}</Text>
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
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 24,
    paddingHorizontal: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: 14,
    color: '#D1FAE5',
    marginBottom: 4,
  },
  name: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  notificationButton: {
    position: 'relative',
  },
  notificationText: {
    fontSize: 24,
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#EF4444',
    borderRadius: 10,
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: 'bold',
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
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#0F766E',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchButtonText: {
    fontSize: 20,
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
    backgroundColor: '#FFFFFF',
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
    fontWeight: 'bold',
    color: '#0F766E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 10,
    color: '#6B7280',
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
    fontWeight: 'bold',
    color: '#1F2937',
  },
  seeAllText: {
    fontSize: 14,
    color: '#0F766E',
    fontWeight: '600',
  },
  quickActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  actionIcon: {
    fontSize: 36,
    marginBottom: 8,
  },
  actionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  actionSubtitle: {
    fontSize: 12,
    color: '#6B7280',
  },
  workerCard: {
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#0F766E',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  workerAvatarText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
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
    fontWeight: '600',
    color: '#1F2937',
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
    color: '#6B7280',
    marginBottom: 4,
  },
  workerStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  workerRating: {
    fontSize: 13,
    color: '#F59E0B',
    fontWeight: '600',
  },
  workerJobs: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 4,
  },
  workerRate: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 4,
  },
  workerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  viewProfileButton: {
    flex: 1,
    height: 40,
    backgroundColor: '#F3F4F6',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  viewProfileButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  requestButton: {
    flex: 1,
    height: 40,
    backgroundColor: '#0F766E',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  requestButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  jobCard: {
    backgroundColor: '#FFFFFF',
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
    fontWeight: '600',
    color: '#1F2937',
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
    fontWeight: '600',
  },
  statusTextActive: {
    color: '#1E40AF',
  },
  statusTextInProgress: {
    color: '#92400E',
  },
  jobCategory: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 8,
  },
  jobFooter: {
    flexDirection: 'row',
  },
  jobInfo: {
    fontSize: 12,
    color: '#9CA3AF',
    marginRight: 4,
  },
  categoriesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  categoryCard: {
    width: '30%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  categoryIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  categoryName: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1F2937',
    textAlign: 'center',
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
    color: '#6B7280',
  },
});
