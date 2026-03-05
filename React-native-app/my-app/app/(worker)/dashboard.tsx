import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import apiService from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';

interface DirectHireRequest {
  id: number;
  client_name: string;
  duration_type: string;
  offered_rate: number;
  total_amount: number;
  status: string;
  created_at: string;
  message?: string;
}

interface AssignedJob {
  id: number;
  title: string;
  status: string;
  urgency: string;
  location: string;
  city: string;
  total_price?: number;
  created_at: string;
  client_name: string;
  client_phone?: string;
  category_name?: string;
}

interface PendingAssignment {
  id: number;
  category_name: string;
  urgency: string;
  status: string;
  created_at: string;
  client_name: string;
}

export default function WorkerDashboard() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [isAvailable, setIsAvailable] = useState(true);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pendingRequests, setPendingRequests] = useState<DirectHireRequest[]>([]);
  const [assignedJobs, setAssignedJobs] = useState<AssignedJob[]>([]);
  const [pendingAssignments, setPendingAssignments] = useState<PendingAssignment[]>([]);
  const [stats, setStats] = useState({
    assigned_jobs: 0,
    active_jobs: 0,
    completed_jobs: 0,
    pending_jobs: 0,
  });
  
  // Check if user is professional worker
  const isProfessional = user?.workerType === 'professional';

  // Redirect if wrong user type
  useEffect(() => {
    let mounted = true;
    
    if (user && user.userType !== 'worker') {
      console.log('Wrong user type for worker dashboard, redirecting to client');
      router.replace('/(client)/dashboard');
      return;
    }
    
    // Only load data if user type is correct and component is mounted
    if (user && user.userType === 'worker' && mounted) {
      fetchDashboardData();
    }
    
    return () => {
      mounted = false;
    };
  }, [user]);

  // Create theme-aware styles
  const styles = StyleSheet.create({
    container: {
      flex: 1,
    },
    greetingSection: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 20,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    greeting: {
      fontSize: 15,
      marginBottom: 6,
      fontFamily: theme.fontMedium,
      color: theme.text,
    },
    name: {
      fontSize: 24,
      fontFamily: theme.fontBold,
      color: theme.textSecondary,
    },
    scrollContent: {
      padding: 16,
    },
    availabilityCard: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 18,
      marginBottom: 16,
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    availabilityInfo: {
      flex: 1,
      marginRight: 12,
    },
    availabilityTitle: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 4,
    },
    availabilitySubtitle: {
      fontSize: 12,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
    statsContainer: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 12,
      marginBottom: 20,
    },
    statCard: {
      flex: 1,
      minWidth: '47%',
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 20,
      alignItems: 'center',
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    statValue: {
      fontSize: 28,
      fontFamily: theme.fontBold,
      color: theme.primary,
      marginBottom: 6,
    },
    statLabel: {
      fontSize: 13,
      fontFamily: theme.fontMedium,
      color: theme.textSecondary,
      textAlign: 'center',
    },
    section: {
      marginBottom: 20,
    },
    activeServiceBanner: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      borderRadius: 12,
      padding: 14,
      marginBottom: 16,
    },
    activeServiceBannerText: {
      flex: 1,
      color: '#fff',
      fontSize: 15,
      fontWeight: '600',
    },
    sectionTitle: {
      fontSize: 20,
      fontFamily: theme.fontBold,
      color: theme.text,
      marginBottom: 14,
      paddingHorizontal: 2,
    },
    requestCard: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 18,
      marginBottom: 12,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    requestHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: 12,
    },
    clientName: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 4,
    },
    requestTime: {
      fontSize: 12,
      fontFamily: theme.fontRegular,
      color: theme.textTertiary,
    },
    amountBadge: {
      backgroundColor: isDark ? theme.primaryDark : '#ECFDF5',
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 8,
    },
    amountText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.primary,
    },
    requestDetails: {
      marginBottom: 16,
    },
    detailRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginBottom: 8,
    },
    detailLabel: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
    detailValue: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
    },
    requestActions: {
      flexDirection: 'row',
      gap: 12,
    },
    rejectButton: {
      flex: 1,
      height: 44,
      backgroundColor: theme.card,
      borderRadius: 10,
      justifyContent: 'center',
      alignItems: 'center',
      borderWidth: 1,
      borderColor: theme.border,
    },
    rejectButtonText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.textSecondary,
    },
    acceptButton: {
      flex: 2,
      height: 44,
      backgroundColor: theme.primary,
      borderRadius: 10,
      justifyContent: 'center',
      alignItems: 'center',
    },
    acceptButtonText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: '#FFFFFF',
    },
    emptyState: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 40,
      alignItems: 'center',
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    emptyStateText: {
      fontSize: 56,
      marginBottom: 16,
    },
    emptyStateTitle: {
      fontSize: 18,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 6,
    },
    emptyStateSubtitle: {
      fontSize: 15,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
      textAlign: 'center',
    },
    infoCard: {
      borderRadius: 12,
      padding: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    infoCardTitle: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      marginBottom: 4,
    },
    infoCardSubtitle: {
      fontSize: 13,
      fontFamily: theme.fontRegular,
    },
    actionButtonsContainer: {
      gap: 12,
      marginBottom: 20,
    },
    browseJobsButton: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      paddingVertical: 16,
      paddingHorizontal: 24,
      borderRadius: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 3 },
      shadowOpacity: 0.2,
      shadowRadius: 6,
      elevation: 5,
    },
    browseJobsButtonText: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: '#FFFFFF',
    },
    savedJobsButton: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      paddingVertical: 14,
      paddingHorizontal: 24,
      borderRadius: 16,
      borderWidth: 2,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 2,
    },
    savedJobsButtonText: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
    },
    quickActions: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 12,
    },
    actionButton: {
      flex: 1,
      minWidth: '47%',
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 24,
      alignItems: 'center',
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 8,
      elevation: 3,
    },
    actionIcon: {
      fontSize: 36,
      marginBottom: 10,
    },
    actionText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      textAlign: 'center',
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    loadingText: {
      marginTop: 12,
      fontSize: 16,
      fontFamily: theme.fontRegular,
    },
    pendingAlert: {
      borderRadius: 12,
      padding: 16,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    alertContent: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 12,
    },
    alertIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: '#FEF3C7',
      justifyContent: 'center',
      alignItems: 'center',
    },
    alertText: {
      flex: 1,
    },
    alertTitle: {
      fontSize: 15,
      fontFamily: theme.fontSemiBold,
      color: '#92400E',
      marginBottom: 2,
    },
    alertSubtitle: {
      fontSize: 13,
      fontFamily: theme.fontRegular,
      color: '#78350F',
    },
    quickActionsContainer: {
      flexDirection: 'row',
      gap: 12,
      marginBottom: 20,
    },
    quickActionCard: {
      flex: 1,
      borderRadius: 12,
      padding: 20,
      alignItems: 'center',
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 4,
      elevation: 3,
      position: 'relative',
    },
    quickActionTitle: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      marginTop: 8,
    },
    badge: {
      position: 'absolute',
      top: 8,
      right: 8,
      backgroundColor: '#EF4444',
      borderRadius: 12,
      minWidth: 24,
      height: 24,
      justifyContent: 'center',
      alignItems: 'center',
      paddingHorizontal: 6,
    },
    badgeText: {
      color: '#FFFFFF',
      fontSize: 12,
      fontFamily: theme.fontBold,
    },
    statusBadge: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 12,
      minWidth: 50,
      alignItems: 'center',
    },
    statusText: {
      fontSize: 10,
      fontFamily: theme.fontBold,
      color: '#FFFFFF',
    },
    viewAllButton: {
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderRadius: 10,
      alignItems: 'center',
      marginTop: 12,
    },
    viewAllText: {
      fontSize: 14,
      fontFamily: theme.fontSemiBold,
      color: '#FFFFFF',
    },
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async (isMounted = () => true) => {
    try {
      setLoading(true);
      const [assignedJobsData, statsData, pendingAssignmentsData] = await Promise.all([
        apiService.getWorkerAssignments().catch(err => {
          console.error('Error fetching assigned jobs:', err);
          return { results: [] };
        }),
        apiService.getWorkerStats().catch(err => {
          console.error('Error fetching stats:', err);
          return {
            assigned_jobs: 0,
            active_jobs: 0,
            completed_jobs: 0,
            pending_jobs: 0,
          };
        }),
        apiService.getPendingAssignments().catch(err => {
          console.error('Error fetching pending assignments:', err);
          return { results: [] };
        }),
      ]);
      
      // Only update state if component is still mounted
      if (isMounted()) {
        // Handle paginated response from getWorkerAssignments
        const assignmentsList = assignedJobsData?.results || (Array.isArray(assignedJobsData) ? assignedJobsData : []);
        setAssignedJobs(assignmentsList);
        setPendingAssignments(pendingAssignmentsData?.results || pendingAssignmentsData || []);
        setStats(statsData || {
          assigned_jobs: 0,
          active_jobs: 0,
          completed_jobs: 0,
          pending_jobs: 0,
        });
      }
    } catch (error: any) {
      console.error('Error fetching dashboard data:', error);
      console.error('Error details:', error?.response?.data || error?.message);
    } finally {
      if (isMounted()) {
        setLoading(false);
      }
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchDashboardData();
    setRefreshing(false);
  };

  const handleAcceptRequest = async (requestId: number) => {
    Alert.alert(
      'Accept Request',
      'Are you sure you want to accept this job request?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Accept',
          onPress: async () => {
            try {
              await apiService.acceptDirectHireRequest(requestId);
              Alert.alert('Success', 'Request accepted! Client will be notified.');
              fetchDashboardData(); // Refresh data
            } catch (error) {
              console.error('Error accepting request:', error);
              Alert.alert('Error', 'Failed to accept request. Please try again.');
            }
          },
        },
      ]
    );
  };

  const handleRejectRequest = async (requestId: number) => {
    Alert.alert(
      'Reject Request',
      'Are you sure you want to reject this job request?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reject',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.rejectDirectHireRequest(requestId);
              Alert.alert('Request Rejected', 'You declined the job request.');
              fetchDashboardData(); // Refresh data
            } catch (error) {
              console.error('Error rejecting request:', error);
              Alert.alert('Error', 'Failed to reject request. Please try again.');
            }
          },
        },
      ]
    );
  };

  const toggleAvailability = async () => {
    const newValue = !isAvailable;
    try {
      await apiService.updateWorkerAvailability(newValue);
      setIsAvailable(newValue);
      Alert.alert(
        'Success', 
        newValue ? 'You are now available for work' : 'You are now unavailable',
        [{ text: 'OK' }]
      );
    } catch (error) {
      console.error('Error updating availability:', error);
      Alert.alert('Error', 'Failed to update availability');
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      {/* Header Component */}
      <Header 
        showNotifications 
        showSearch 
        onNotificationPress={() => Alert.alert('Notifications', 'No new notifications')}
        onSearchPress={() => router.push('/(worker)/jobs')}
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
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.primary}
          />
        }
      >
        {/* Greeting Section */}
        <View style={[styles.greetingSection, { backgroundColor: theme.surface }]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.greeting, { color: theme.text }]}>Welcome back! 👋</Text>
              <Text style={[styles.name, { color: theme.textSecondary }]}>{user?.firstName} {user?.lastName}</Text>
            </View>
            {/* Verification Status Badge */}
            {user?.verificationStatus && (
              <View style={{
                paddingHorizontal: 12,
                paddingVertical: 6,
                borderRadius: 12,
                backgroundColor: 
                  user.verificationStatus === 'verified' ? '#ECFDF5' :
                  user.verificationStatus === 'rejected' ? '#FEF2F2' : '#FEF3C7',
              }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <Ionicons 
                    name={
                      user.verificationStatus === 'verified' ? 'checkmark-circle' :
                      user.verificationStatus === 'rejected' ? 'close-circle' : 'time'
                    }
                    size={16}
                    color={
                      user.verificationStatus === 'verified' ? '#059669' :
                      user.verificationStatus === 'rejected' ? '#DC2626' : '#D97706'
                    }
                  />
                  <Text style={{
                    fontSize: 12,
                    fontFamily: theme.fontSemiBold,
                    color: 
                      user.verificationStatus === 'verified' ? '#059669' :
                      user.verificationStatus === 'rejected' ? '#DC2626' : '#D97706',
                  }}>
                    {user.verificationStatus === 'verified' ? 'Verified' :
                     user.verificationStatus === 'rejected' ? 'Not Verified' : 'Pending'}
                  </Text>
                </View>
              </View>
            )}
          </View>
        </View>
        {/* Availability Toggle */}
        <View style={styles.availabilityCard}>
          <View style={styles.availabilityInfo}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons 
                name={isAvailable ? 'checkmark-circle' : 'pause-circle'} 
                size={20} 
                color={isAvailable ? theme.success : theme.textSecondary} 
                style={{ marginRight: 8 }}
              />
              <Text style={styles.availabilityTitle}>
                {isAvailable ? 'Available for Work' : 'Currently Unavailable'}
              </Text>
            </View>
            <Text style={styles.availabilitySubtitle}>
              {isAvailable
                ? 'Clients can send you direct hire requests'
                : 'You are not visible to clients'}
            </Text>
          </View>
          <Switch
            value={isAvailable}
            onValueChange={toggleAvailability}
            trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
            thumbColor={isAvailable ? '#0F766E' : '#9CA3AF'}
          />
        </View>

        {/* Pending Assignments Alert */}
        {pendingAssignments.length > 0 && (
          <TouchableOpacity
            style={[styles.pendingAlert, { backgroundColor: '#FEF3C7', borderWidth: 2, borderColor: '#F59E0B' }]}
            onPress={() => router.push('/(worker)/service-assignments')}
          >
            <View style={styles.alertContent}>
              <View style={styles.alertIcon}>
                <Ionicons name="alert-circle" size={28} color="#D97706" />
              </View>
              <View style={styles.alertText}>
                <Text style={[styles.alertTitle, { fontSize: 16 }]}>
                  🔔 {pendingAssignments.length} Pending Assignment{pendingAssignments.length > 1 ? 's' : ''}
                </Text>
                <Text style={styles.alertSubtitle}>
                  You have service requests waiting for your response
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={28} color="#D97706" />
            </View>
          </TouchableOpacity>
        )}

        {/* Browse Jobs Button - Professional Workers Only */}
        {isProfessional && (
          <View style={styles.actionButtonsContainer}>
            <TouchableOpacity
              style={[styles.browseJobsButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push('/browse-jobs' as any)}
            >
              <Ionicons name="search" size={20} color="#FFFFFF" />
              <Text style={styles.browseJobsButtonText}>Browse & Apply for Jobs</Text>
              <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.savedJobsButton, { backgroundColor: theme.surface, borderColor: theme.primary }]}
              onPress={() => router.push('/saved-jobs' as any)}
            >
              <Ionicons name="heart" size={20} color={theme.primary} />
              <Text style={[styles.savedJobsButtonText, { color: theme.primary }]}>Saved Jobs</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Stats Grid */}
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.assigned_jobs}</Text>
            <Text style={styles.statLabel}>Assigned Jobs</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.active_jobs}</Text>
            <Text style={styles.statLabel}>Active</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.completed_jobs}</Text>
            <Text style={styles.statLabel}>Completed</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.pending_jobs}</Text>
            <Text style={styles.statLabel}>Pending</Text>
          </View>
        </View>

        {/* Active Service Quick Access */}
        {stats.active_jobs > 0 && (
          <TouchableOpacity
            style={[styles.activeServiceBanner, { backgroundColor: theme.primary }]}
            onPress={() => router.push('/(worker)/active-service' as any)}
          >
            <Ionicons name="time" size={22} color="#fff" />
            <Text style={styles.activeServiceBannerText}>You have an active service — Tap to manage</Text>
            <Ionicons name="chevron-forward" size={20} color="#fff" />
          </TouchableOpacity>
        )}

        {/* Assigned Jobs Section */}
        {assignedJobs.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Your Assigned Jobs ({assignedJobs.length})</Text>
            {assignedJobs.slice(0, 3).map((job) => (
              <TouchableOpacity 
                key={job.id}
                style={[styles.infoCard, { backgroundColor: theme.surface }]}
                onPress={() => {
                  if (job.status === 'in_progress') {
                    router.push('/(worker)/active-service' as any);
                  } else {
                    router.push(`/(worker)/service-assignment/${job.id}` as any);
                  }
                }}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <View style={[
                    styles.statusBadge, 
                    { 
                      backgroundColor: 
                        job.status === 'pending' ? '#FFA500' :
                        job.status === 'in_progress' ? '#2196F3' :
                        job.status === 'completed' ? '#4CAF50' : '#FF6B6B'
                    }
                  ]}>
                    <Text style={styles.statusText}>
                      {job.status === 'pending' ? 'NEW' : 
                       job.status === 'in_progress' ? 'ACTIVE' : 
                       job.status === 'completed' ? 'DONE' : 'ASSIGNED'}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.infoCardTitle, { color: theme.text }]}>
                      {job.title}
                    </Text>
                    <Text style={[styles.infoCardSubtitle, { color: theme.textSecondary }]}>
                      Client: {job.client_name}
                    </Text>
                    <Text style={[styles.infoCardSubtitle, { color: theme.textSecondary }]}>
                      {job.total_price ? `SDG ${job.total_price}` : 'Price not set'}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={24} color={theme.textSecondary} />
                </View>
              </TouchableOpacity>
            ))}
            {assignedJobs.length > 3 && (
              <TouchableOpacity 
                style={[styles.viewAllButton, { backgroundColor: theme.primary }]}
                onPress={() => router.push('/(worker)/service-assignments' as any)}
              >
                <Text style={styles.viewAllText}>
                  View All {assignedJobs.length} Jobs
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Job Applications Section - for professionals only */}
        {isProfessional && stats.total_applications > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>My Applications</Text>
            <TouchableOpacity 
              style={[styles.infoCard, { backgroundColor: theme.surface }]}
              onPress={() => router.push('/applications' as any)}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <Ionicons name="document-text" size={32} color={theme.primary} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.infoCardTitle, { color: theme.text }]}>
                    {stats.total_applications} {stats.total_applications === 1 ? 'Application' : 'Applications'}
                  </Text>
                  <Text style={[styles.infoCardSubtitle, { color: theme.textSecondary }]}>
                    {stats.accepted_applications} accepted • {stats.total_applications - stats.accepted_applications} pending
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={24} color={theme.textSecondary} />
              </View>
            </TouchableOpacity>
          </View>
        )}

        {/* Pending Requests */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pending Requests ({pendingRequests.length})</Text>
          {pendingRequests.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="mail-open-outline" size={48} color={theme.textSecondary} style={{ marginBottom: 12 }} />
              <Text style={styles.emptyStateTitle}>No pending requests</Text>
              <Text style={styles.emptyStateSubtitle}>
                New job requests will appear here
              </Text>
            </View>
          ) : (
            pendingRequests.map((request) => (
              <View key={request.id} style={styles.requestCard}>
                <View style={styles.requestHeader}>
                  <View>
                    <Text style={styles.clientName}>{request.client_name}</Text>
                    <Text style={styles.requestTime}>{new Date(request.created_at).toLocaleDateString()}</Text>
                  </View>
                  <View style={styles.amountBadge}>
                    <Text style={styles.amountText}>
                      SDG {request.offered_rate}
                    </Text>
                  </View>
                </View>

                <View style={styles.requestDetails}>
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Duration:</Text>
                    <Text style={styles.detailValue}>{request.duration_type}</Text>
                  </View>
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Total Amount:</Text>
                    <Text style={styles.detailValue}>
                      SDG {request.total_amount.toLocaleString()}
                    </Text>
                  </View>
                </View>

                <View style={styles.requestActions}>
                  <TouchableOpacity
                    style={styles.rejectButton}
                    onPress={() => handleRejectRequest(request.id)}
                  >
                    <Text style={styles.rejectButtonText}>Decline</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.acceptButton}
                    onPress={() => handleAcceptRequest(request.id)}
                  >
                    <Text style={styles.acceptButtonText}>Accept Job</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.quickActions}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/notifications' as any)}
            >
              <Ionicons name="notifications-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>Notifications</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/analytics' as any)}
            >
              <Ionicons name="analytics-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>Analytics</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/profile')}
            >
              <Ionicons name="person-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>My Profile</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/earnings')}
            >
              <Ionicons name="cash-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>Earnings</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/documents')}
            >
              <Ionicons name="document-text-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>Documents</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
      )}
    </View>
  );
}
