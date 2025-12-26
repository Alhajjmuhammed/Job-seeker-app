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
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface DirectHireRequest {
  id: number;
  clientName: string;
  durationType: string;
  offeredRate: number;
  totalAmount: number;
  status: string;
  createdAt: string;
  message?: string;
}

export default function WorkerJobsScreen() {
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [directRequests, setDirectRequests] = useState<DirectHireRequest[]>([]);

  useEffect(() => {
    loadDirectRequests();
  }, []);

  const loadDirectRequests = async () => {
    try {
      setLoading(true);
      const requests = await apiService.getDirectHireRequests();
      setDirectRequests(requests.map((req: any) => ({
        id: req.id,
        clientName: req.client_name || 'Client',
        durationType: req.duration_type || 'hourly',
        offeredRate: parseFloat(req.offered_rate || '0'),
        totalAmount: parseFloat(req.total_amount || '0'),
        status: req.status,
        createdAt: new Date(req.created_at).toLocaleDateString(),
        message: req.message,
      })));
    } catch (error) {
      console.error('Error loading direct requests:', error);
      Alert.alert('Error', 'Failed to load direct hire requests');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDirectRequests();
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
              loadDirectRequests();
            } catch (error) {
              Alert.alert('Error', 'Failed to accept request');
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
              Alert.alert('Success', 'Request rejected.');
              loadDirectRequests();
            } catch (error) {
              Alert.alert('Error', 'Failed to reject request');
            }
          },
        },
      ]
    );
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted': return '#4CAF50';
      case 'rejected': return '#F44336';
      case 'pending': return '#FF9800';
      default: return '#666';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'accepted': return 'checkmark-circle';
      case 'rejected': return 'close-circle';
      case 'pending': return 'time';
      default: return 'help-circle';
    }
  };

  const renderRequestCard = (request: DirectHireRequest) => (
    <View key={request.id} style={[styles.requestCard, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
      <View style={styles.requestHeader}>
        <View>
          <Text style={[styles.clientName, { color: theme.text }]}>
            <Ionicons name="person" size={18} color={theme.primary} /> {request.clientName}
          </Text>
          <Text style={[styles.requestDate, { color: theme.textSecondary }]}>{request.createdAt}</Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(request.status) }]}>
          <Ionicons name={getStatusIcon(request.status) as any} size={16} color="#FFF" />
          <Text style={styles.statusText}>{request.status.toUpperCase()}</Text>
        </View>
      </View>

      {request.message && (
        <View style={[styles.messageContainer, { backgroundColor: isDark ? theme.border : '#F9FAFB' }]}>
          <Ionicons name="mail-outline" size={16} color={theme.textSecondary} />
          <Text style={[styles.messageText, { color: theme.textSecondary }]}>{request.message}</Text>
        </View>
      )}

      <View style={styles.requestDetails}>
        <View style={styles.detailRow}>
          <Ionicons name="time-outline" size={18} color={theme.textSecondary} />
          <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>Duration:</Text>
          <Text style={[styles.detailValue, { color: theme.text }]}>{request.durationType}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="cash-outline" size={18} color={isDark ? '#81C784' : '#2E7D32'} />
          <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>Offered Rate:</Text>
          <Text style={[styles.detailValue, styles.rateText, { color: isDark ? '#81C784' : '#2E7D32' }]}>${request.offeredRate}</Text>
        </View>
        <View style={styles.detailRow}>
          <Ionicons name="card-outline" size={18} color={isDark ? '#81C784' : '#2E7D32'} />
          <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>Total:</Text>
          <Text style={[styles.detailValue, styles.totalAmount, { color: isDark ? '#81C784' : '#2E7D32' }]}>${request.totalAmount}</Text>
        </View>
      </View>

      {request.status === 'pending' && (
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionButton, styles.rejectButton]}
            onPress={() => handleRejectRequest(request.id)}
          >
            <Ionicons name="close-circle" size={20} color="#FFF" />
            <Text style={styles.actionButtonText}>Reject</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, styles.acceptButton]}
            onPress={() => handleAcceptRequest(request.id)}
          >
            <Ionicons name="checkmark-circle" size={20} color="#FFF" />
            <Text style={styles.actionButtonText}>Accept</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      {/* Header Component */}
      <Header 
        showNotifications 
        showSearch 
        onNotificationPress={() => Alert.alert('Notifications', 'No new notifications')}
        onSearchPress={() => Alert.alert('Search', 'Search coming soon')}
      />

      {/* Info Banner */}
      <View style={[styles.infoBanner, { backgroundColor: isDark ? 'rgba(25, 118, 210, 0.1)' : '#E3F2FD' }]}>
        <Ionicons name="information-circle" size={20} color={theme.primary} />
        <Text style={[styles.infoText, { color: isDark ? '#90CAF9' : '#1565C0' }]}>
          Clients will find and request you directly. Accept or reject requests below.
        </Text>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading requests...</Text>
        </View>
      ) : (
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.primary]} />
        }
      >
            {/* Direct Hire Requests */}
            {directRequests.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="mail-open-outline" size={48} color={theme.textSecondary} style={{ marginBottom: 12 }} />
                <Text style={[styles.emptyText, { color: theme.text }]}>No hire requests yet</Text>
                <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>Keep your profile updated and wait for clients to find you!</Text>
              </View>
            ) : (
              directRequests.map(renderRequestCard)
            )}
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
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontFamily: 'Poppins_700Bold',
    color: '#FFFFFF',
  },
  headerSubtitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#FFFFFF',
    marginTop: 4,
    opacity: 0.9,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    padding: 16,
    marginHorizontal: 20,
    marginTop: 16,
    borderRadius: 8,
    gap: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#1565C0',
    lineHeight: 20,
  },
  scrollContent: {
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 64,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    color: '#374151',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    textAlign: 'center',
    paddingHorizontal: 40,
  },
  requestCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  requestHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  clientName: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    color: '#1F2937',
    marginBottom: 4,
  },
  requestDate: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#9CA3AF',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  statusText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
  },
  messageContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#F9FAFB',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  messageText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#4B5563',
    lineHeight: 20,
  },
  requestDetails: {
    gap: 12,
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_500Medium',
    color: '#6B7280',
  },
  detailValue: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    color: '#1F2937',
  },
  rateText: {
    color: '#2E7D32',
  },
  totalAmount: {
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    color: '#2E7D32',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 6,
  },
  acceptButton: {
    backgroundColor: '#4CAF50',
  },
  rejectButton: {
    backgroundColor: '#F44336',
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
});
