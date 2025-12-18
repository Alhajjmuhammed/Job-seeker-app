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
import apiService from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

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

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
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
      setPendingRequests(requestsData || []);
      setStats(statsData || {
        pending_requests: 0,
        active_jobs: 0,
        total_applications: 0,
        accepted_applications: 0,
      });
    } catch (error: any) {
      console.error('Error fetching dashboard data:', error);
      console.error('Error details:', error?.response?.data || error?.message);
    } finally {
      setLoading(false);
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
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome back! 👋</Text>
          <Text style={styles.name}>{user?.firstName} {user?.lastName}</Text>
        </View>
        <TouchableOpacity style={styles.notificationButton}>
          <Text style={styles.notificationText}>🔔</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>2</Text>
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
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#0F766E"
          />
        }
      >
        {/* Availability Toggle */}
        <View style={styles.availabilityCard}>
          <View style={styles.availabilityInfo}>
            <Text style={styles.availabilityTitle}>
              {isAvailable ? '✅ Available for Work' : '⏸️ Currently Unavailable'}
            </Text>
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
              <Text style={styles.emptyStateText}>📭</Text>
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
              <Text style={styles.actionIcon}>�</Text>
              <Text style={styles.actionText}>View Requests</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/profile')}
            >
              <Text style={styles.actionIcon}>👤</Text>
              <Text style={styles.actionText}>My Profile</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/earnings')}
            >
              <Text style={styles.actionIcon}>💰</Text>
              <Text style={styles.actionText}>Earnings</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => router.push('/(worker)/documents')}
            >
              <Text style={styles.actionIcon}>📄</Text>
              <Text style={styles.actionText}>Documents</Text>
            </TouchableOpacity>
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
  availabilityCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  availabilityInfo: {
    flex: 1,
    marginRight: 12,
  },
  availabilityTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  availabilitySubtitle: {
    fontSize: 12,
    color: '#6B7280',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    minWidth: '47%',
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
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0F766E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  requestCard: {
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
  requestHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  clientName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  requestTime: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  amountBadge: {
    backgroundColor: '#ECFDF5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  amountText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F766E',
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
    color: '#6B7280',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  requestActions: {
    flexDirection: 'row',
    gap: 12,
  },
  rejectButton: {
    flex: 1,
    height: 44,
    backgroundColor: '#F3F4F6',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  rejectButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  acceptButton: {
    flex: 2,
    height: 44,
    backgroundColor: '#0F766E',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  acceptButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  emptyState: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
  },
  emptyStateText: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyStateTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  emptyStateSubtitle: {
    fontSize: 14,
    color: '#6B7280',
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
    fontSize: 32,
    marginBottom: 8,
  },
  actionText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1F2937',
    textAlign: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F3F4F6',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
});
