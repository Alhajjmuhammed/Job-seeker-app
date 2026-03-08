import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
  RefreshControl,
} from 'react-native';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';

interface ServiceRequestDetail {
  id: number;
  title: string;
  description: string;
  category_name: string;
  status: string;
  urgency: string;
  location: string;
  city: string;
  preferred_date?: string;
  preferred_time?: string;
  estimated_duration_hours: number;
  client_notes?: string;
  created_at: string;
  assigned_worker?: {
    id: number;
    full_name: string;
    phone_number: string;
    email: string;
    profile_picture?: string;
    rating: number;
  };
  worker_accepted?: boolean;
  rejection_reason?: string;
  client_rating?: number;
  client_review?: string;
}

interface TimeLog {
  id: number;
  clock_in: string;
  clock_out?: string;
  duration_hours?: number;
  clock_in_location: string;
  clock_out_location?: string;
  notes?: string;
}

export default function ServiceRequestDetailScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [request, setRequest] = useState<ServiceRequestDetail | null>(null);
  const [timeLogs, setTimeLogs] = useState<TimeLog[]>([]);
  const [canceling, setCanceling] = useState(false);
  const [completing, setCompleting] = useState(false);

  const loadRequestDetail = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.getServiceRequestDetail(Number(id));
      setRequest(response.service_request || response);
      setTimeLogs(response.time_logs || []);
    } catch (error: any) {
      console.error('Error loading request detail:', error);
      Alert.alert('Error', 'Failed to load request details');
      router.back();
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Load data when screen is focused (including after editing)
  useFocusEffect(
    useCallback(() => {
      loadRequestDetail();
    }, [loadRequestDetail])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await loadRequestDetail();
    setRefreshing(false);
  };

  const handleCancelRequest = () => {
    Alert.alert(
      'Cancel Service Request',
      'Are you sure you want to cancel this request? This action cannot be undone.',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: confirmCancellation,
        },
      ]
    );
  };

  const confirmCancellation = async () => {
    try {
      setCanceling(true);
      await apiService.cancelServiceRequest(Number(id));
      Alert.alert('Success', 'Service request cancelled successfully', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert(
        'Error',
        error.response?.data?.error || 'Failed to cancel request'
      );
    } finally {
      setCanceling(false);
    }
  };

  const handleMarkAsFinished = () => {
    Alert.alert(
      'Mark as Finished',
      'Are you satisfied with the work completed? This will mark the service as finished and you can rate the worker.',
      [
        { text: 'Not Yet', style: 'cancel' },
        {
          text: 'Yes, Finished',
          onPress: confirmCompletion,
        },
      ]
    );
  };

  const confirmCompletion = async () => {
    try {
      setCompleting(true);
      await apiService.completeServiceRequest(Number(id));
      Alert.alert('Success', 'Service marked as finished! You can now rate the worker.', [
        { text: 'OK', onPress: () => loadRequestDetail() },
      ]);
    } catch (error: any) {
      Alert.alert(
        'Error',
        error.response?.data?.error || 'Failed to mark service as finished'
      );
    } finally {
      setCompleting(false);
    }
  };

  const handleCallWorker = () => {
    if (request?.assigned_worker?.phone_number) {
      Linking.openURL(`tel:${request.assigned_worker.phone_number}`);
    }
  };

  const getStatusColor = (status: string) => {
    const colors = {
      pending: '#FFA500',
      assigned: '#2196F3',
      accepted: '#4CAF50',
      in_progress: '#9C27B0',
      completed: '#4CAF50',
      cancelled: '#F44336',
    };
    return colors[status as keyof typeof colors] || theme.textSecondary;
  };

  const getStatusIcon = (status: string) => {
    const icons = {
      pending: 'time-outline',
      assigned: 'person-add-outline',
      accepted: 'checkmark-circle-outline',
      in_progress: 'play-circle-outline',
      completed: 'checkmark-done-circle-outline',
      cancelled: 'close-circle-outline',
    };
    return icons[status as keyof typeof icons] || 'help-circle-outline';
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const calculateTotalHours = () => {
    return timeLogs.reduce((sum, log) => sum + (log.duration_hours || 0), 0);
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Request Details" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>
            Loading details...
          </Text>
        </View>
      </View>
    );
  }

  if (!request) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Request Details" showBack />
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={64} color={theme.textSecondary} />
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>
            Request not found
          </Text>
        </View>
      </View>
    );
  }

  const canCancel = ['pending', 'assigned'].includes(request.status);
  const canEdit = request.status === 'pending';

  const handleEditRequest = () => {
    router.push(`/(client)/edit-service-request/${request.id}` as any);
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Request Details" showBack />

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Status Card */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={[styles.statusBanner, { backgroundColor: getStatusColor(request.status) }]}>
            <Ionicons name={getStatusIcon(request.status) as any} size={24} color="#FFFFFF" />
            <Text style={styles.statusBannerText}>
              {request.status.replace('_', ' ').toUpperCase()}
            </Text>
          </View>

          <Text style={[styles.title, { color: theme.text }]}>{request.title}</Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {request.category_name}
          </Text>

          {/* Edit Button */}
          {canEdit && (
            <TouchableOpacity
              style={[styles.editButton, { backgroundColor: theme.primary + '15', borderColor: theme.primary }]}
              onPress={handleEditRequest}
            >
              <Ionicons name="create-outline" size={20} color={theme.primary} />
              <Text style={[styles.editButtonText, { color: theme.primary }]}>Edit Request</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Request Details */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Request Details</Text>
          
          <View style={styles.detailRow}>
            <Ionicons name="document-text-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>Description:</Text>
          </View>
          <Text style={[styles.description, { color: theme.text }]}>
            {request.description}
          </Text>

          <View style={styles.detailRow}>
            <Ionicons name="location-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailText, { color: theme.text }]}>
              {request.location}, {request.city}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="time-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailText, { color: theme.text }]}>
              Estimated Duration: {request.estimated_duration_hours} hours
            </Text>
          </View>

          {request.preferred_date && (
            <View style={styles.detailRow}>
              <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailText, { color: theme.text }]}>
                Preferred Date: {new Date(request.preferred_date).toLocaleDateString()}
                {request.preferred_time && ` at ${request.preferred_time}`}
              </Text>
            </View>
          )}

          {request.client_notes && (
            <View style={styles.detailRow}>
              <Ionicons name="chatbox-ellipses-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>Client Notes:</Text>
            </View>
          )}
          {request.client_notes && (
            <Text style={[styles.description, { color: theme.text, marginLeft: 28 }]}>
              {request.client_notes}
            </Text>
          )}

          <View style={styles.detailRow}>
            <Ionicons name="flag-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailText, { color: theme.text }]}>
              Urgency: {request.urgency?.toUpperCase()}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailText, { color: theme.textSecondary }]}>
              Requested: {formatDateTime(request.created_at)}
            </Text>
          </View>
        </View>

        {/* Assigned Worker */}
        {request.assigned_worker && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Assigned Worker
            </Text>

            <View style={styles.workerCard}>
              <View style={styles.workerHeader}>
                <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
                  <Text style={styles.avatarText}>
                    {request.assigned_worker.full_name?.charAt(0) || 'W'}
                  </Text>
                </View>
                <View style={styles.workerInfo}>
                  <Text style={[styles.workerName, { color: theme.text }]}>
                    {request.assigned_worker.full_name || 'Worker'}
                  </Text>
                  {request.assigned_worker.rating && request.assigned_worker.rating > 0 && (
                    <View style={styles.ratingRow}>
                      <Ionicons name="star" size={16} color="#FFA500" />
                      <Text style={[styles.ratingText, { color: theme.textSecondary }]}>
                        {request.assigned_worker.rating.toFixed(1)}
                      </Text>
                    </View>
                  )}
                </View>
              </View>

              {request.worker_accepted === true && (
                <View style={[styles.acceptedBadge, { backgroundColor: '#4CAF50' }]}>
                  <Ionicons name="checkmark-circle" size={16} color="#FFFFFF" />
                  <Text style={styles.acceptedText}>Worker Accepted</Text>
                </View>
              )}

              {request.worker_accepted === false && (
                <View style={[styles.rejectedBadge, { backgroundColor: '#F44336' }]}>
                  <Ionicons name="close-circle" size={16} color="#FFFFFF" />
                  <Text style={styles.rejectedText}>Worker Rejected</Text>
                  {request.rejection_reason && (
                    <Text style={styles.rejectionReason}>
                      Reason: {request.rejection_reason}
                    </Text>
                  )}
                </View>
              )}

              {request.worker_accepted === null && (
                <View style={[styles.pendingBadge, { backgroundColor: '#FFA500' }]}>
                  <Ionicons name="time" size={16} color="#FFFFFF" />
                  <Text style={styles.pendingText}>Awaiting Worker Response</Text>
                </View>
              )}

              {/* Contact Button */}
              {request.worker_accepted === true && (
                <TouchableOpacity
                  style={[styles.callWorkerButton, { backgroundColor: theme.primary }]}
                  onPress={handleCallWorker}
                >
                  <Ionicons name="call" size={24} color="#FFFFFF" />
                  <Text style={styles.callWorkerButtonText}>Call Worker</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}

        {/* Time Logs */}
        {timeLogs.length > 0 && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Time Tracking</Text>

            <View style={styles.summaryRow}>
              <Text style={[styles.summaryLabel, { color: theme.textSecondary }]}>
                Total Hours:
              </Text>
              <Text style={[styles.summaryValue, { color: theme.primary }]}>
                {calculateTotalHours().toFixed(2)} hrs
              </Text>
            </View>

            <View style={styles.timeLogsList}>
              {timeLogs.map((log) => (
                <View key={log.id} style={[styles.timeLogItem, { backgroundColor: theme.background }]}>
                  <View style={styles.timeLogHeader}>
                    <Ionicons name="time-outline" size={16} color={theme.primary} />
                    <Text style={[styles.timeLogDate, { color: theme.text }]}>
                      {formatDateTime(log.clock_in)}
                    </Text>
                  </View>
                  {log.clock_out ? (
                    <>
                      <Text style={[styles.timeLogDuration, { color: theme.textSecondary }]}>
                        Duration: {log.duration_hours?.toFixed(2)} hours
                      </Text>
                      {log.notes && (
                        <Text style={[styles.timeLogNotes, { color: theme.textSecondary }]}>
                          {log.notes}
                        </Text>
                      )}
                    </>
                  ) : (
                    <View style={[styles.activeLog, { backgroundColor: theme.primary + '20' }]}>
                      <Text style={[styles.activeLogText, { color: theme.primary }]}>
                        ⏱️ Currently Working
                      </Text>
                    </View>
                  )}
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Action Buttons */}
        {canCancel && (
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[styles.cancelButton, { backgroundColor: '#F44336' }]}
              onPress={handleCancelRequest}
              disabled={canceling}
            >
              {canceling ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="close-circle-outline" size={20} color="#FFFFFF" />
                  <Text style={styles.cancelButtonText}>Cancel Request</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Mark as Finished Button - Shows when status is in_progress */}
        {request.status === 'in_progress' && (
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[styles.completeButton, { backgroundColor: '#4CAF50' }]}
              onPress={handleMarkAsFinished}
              disabled={completing}
            >
              {completing ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="checkmark-done-circle-outline" size={20} color="#FFFFFF" />
                  <Text style={styles.completeButtonText}>Mark as Finished</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Rate Worker Button */}
        {request.status === 'completed' && request.assigned_worker && !request.client_rating && (
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[styles.rateButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push(`/(client)/rate-worker/${request.id}` as any)}
            >
              <Ionicons name="star-outline" size={20} color="#FFFFFF" />
              <Text style={styles.rateButtonText}>Rate Worker</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Display Rating if already rated */}
        {request.status === 'completed' && request.client_rating && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Your Rating</Text>
            <View style={styles.ratingDisplay}>
              <View style={styles.starsRow}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <Ionicons
                    key={star}
                    name={star <= request.client_rating! ? 'star' : 'star-outline'}
                    size={24}
                    color="#FFD700"
                  />
                ))}
              </View>
              {request.client_review && (
                <Text style={[styles.reviewText, { color: theme.textSecondary }]}>
                  {request.client_review}
                </Text>
              )}
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    fontSize: 18,
    marginTop: 16,
  },
  content: {
    flex: 1,
  },
  card: {
    margin: 16,
    marginBottom: 0,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  statusBannerText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 8,
  },
  category: {
    fontSize: 16,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  detailLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  detailText: {
    fontSize: 14,
    flex: 1,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
    marginLeft: 28,
  },
  budgetText: {
    fontSize: 16,
    fontWeight: '700',
  },
  workerCard: {
    padding: 12,
  },
  workerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '700',
  },
  workerInfo: {
    flex: 1,
  },
  workerName: {
    fontSize: 18,
    fontWeight: '700',
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
  acceptedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    gap: 6,
  },
  acceptedText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  rejectedBadge: {
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
  },
  rejectedText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  rejectionReason: {
    color: '#FFFFFF',
    fontSize: 12,
    fontStyle: 'italic',
  },
  pendingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    gap: 6,
  },
  pendingText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  callWorkerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 10,
    marginTop: 8,
  },
  callWorkerButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  timeLogsList: {
    marginTop: 12,
  },
  timeLogItem: {
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  timeLogHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  timeLogDate: {
    fontSize: 14,
    fontWeight: '600',
  },
  timeLogDuration: {
    fontSize: 12,
    marginLeft: 22,
    marginBottom: 4,
  },
  timeLogNotes: {
    fontSize: 12,
    marginLeft: 22,
    fontStyle: 'italic',
  },
  activeLog: {
    padding: 8,
    borderRadius: 6,
    marginTop: 4,
  },
  activeLogText: {
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  actionsContainer: {
    padding: 16,
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    gap: 8,
  },
  editButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    gap: 8,
  },
  cancelButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  completeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    gap: 8,
  },
  completeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  rateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    gap: 8,
  },
  rateButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  ratingDisplay: {
    alignItems: 'center',
  },
  starsRow: {
    flexDirection: 'row',
    gap: 4,
    marginBottom: 12,
  },
  reviewText: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
});
