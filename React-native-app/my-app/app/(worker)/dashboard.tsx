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

export default function WorkerDashboard() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [isAvailable, setIsAvailable] = useState(true);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pendingRequests, setPendingRequests] = useState<DirectHireRequest[]>([]);
  const [stats, setStats] = useState({
    pending_requests: 0,
    active_jobs: 0,
    total_applications: 0,
    accepted_applications: 0,
  });

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
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async (isMounted = () => true) => {
    try {
      setLoading(true);
      const [requestsData, statsData] = await Promise.all([
        apiService.getDirectHireRequests().catch(err => {
          console.error('Error fetching requests:', err);
          return [];
        }),
        apiService.getWorkerStats().catch(err => {
          console.error('Error fetching stats:', err);
          return {
            pending_requests: 0,
            active_jobs: 0,
            total_applications: 0,
            accepted_applications: 0,
          };
        }),
      ]);
      
      // Only update state if component is still mounted
      if (isMounted()) {
        setPendingRequests(requestsData || []);
        setStats(statsData || {
          pending_requests: 0,
          active_jobs: 0,
          total_applications: 0,
          accepted_applications: 0,
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

  const toggleAvailability = () => {
    setIsAvailable(!isAvailable);
    // TODO: Update availability status on backend
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
          <Text style={[styles.greeting, { color: theme.text }]}>Welcome back! �</Text>
          <Text style={[styles.name, { color: theme.textSecondary }]}>{user?.firstName} {user?.lastName}</Text>
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

        {/* Stats Grid */}
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.pending_requests}</Text>
            <Text style={styles.statLabel}>Pending Requests</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.active_jobs}</Text>
            <Text style={styles.statLabel}>Active Jobs</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.total_applications || 0}</Text>
            <Text style={styles.statLabel}>Direct Requests</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.accepted_applications || 0}</Text>
            <Text style={styles.statLabel}>Accepted Jobs</Text>
          </View>
        </View>

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
              onPress={() => router.push('/(worker)/jobs')}
            >
              <Ionicons name="briefcase-outline" size={32} color={theme.primary} style={{ marginBottom: 8 }} />
              <Text style={styles.actionText}>View Requests</Text>
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
