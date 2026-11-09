import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Image,
  Modal,
} from 'react-native';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import * as ImagePicker from 'expo-image-picker';
import { useTranslation } from 'react-i18next';

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
  // estimated_duration_hours is a DEPRECATED legacy field (see
  // jobs/service_request_models.py) that the request-creation flow never
  // populates - it's always null/0. The real duration lives in
  // duration_days/duration_type (e.g. "30 days" for a monthly booking).
  estimated_duration_hours?: number;
  duration_days?: number;
  duration_type_display?: string;
  client_notes?: string;
  created_at: string;
  workers_needed?: number; // Number of workers needed
  assignments?: { // Multiple worker assignments (only accepted workers shown)
    id: number;
    assignment_number: number;
    status: string;
    worker: {
      id: number;
      full_name: string;
      phone_number: string;
      email: string;
      profile_picture?: string;
      user_id?: number;
      rating?: number; // Optional - might be null
    };
    worker_response_at?: string; // When worker responded
    worker_rejection_reason?: string; // Rejection reason if rejected
    assigned_at: string; // When admin assigned
  }[];
  worker_accepted?: boolean;
  rejection_reason?: string;
  client_rating?: number;
  client_review?: string;
  // Payment fields
  payment_method?: string;
  payment_transaction_id?: string;
  payment_screenshot?: string;
  payment_verified?: boolean;
  payment_status?: string;
  paid_at?: string;
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
  const { t } = useTranslation();
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [request, setRequest] = useState<ServiceRequestDetail | null>(null);
  const [timeLogs, setTimeLogs] = useState<TimeLog[]>([]);
  const [canceling, setCanceling] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [uploadingScreenshot, setUploadingScreenshot] = useState(false);
  const [imageViewerVisible, setImageViewerVisible] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedWorkerName, setSelectedWorkerName] = useState<string>('');

  const loadRequestDetail = useCallback(async () => {
    try {
      setLoading(true);
      console.log('📋 Loading client service request detail for ID:', id);
      const response = await apiService.getServiceRequestDetail(Number(id));
      console.log('✅ Service request detail loaded:', {
        requestId: response.service_request?.id || response.id,
        status: response.service_request?.status || response.status,
        hasTimeLogs: !!response.time_logs,
        timeLogsCount: response.time_logs?.length || 0,
        assignmentsCount: response.service_request?.assignments?.length || response.assignments?.length || 0
      });
      const requestData = response.service_request || response;
      const timeLogsData = response.time_logs || [];
      console.log('📊 Time logs data:', timeLogsData.map((log: TimeLog) => ({
        id: log.id,
        duration: log.duration_hours,
        clockIn: log.clock_in,
        clockOut: log.clock_out
      })));
      setRequest(requestData);
      setTimeLogs(timeLogsData);
    } catch (error: any) {
      console.error('❌ Error loading request detail:', error);
      console.error('Error details:', error.response?.data || error.message);
      Alert.alert(t('common.error'), t('requestDetail.failedLoad'));
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
    // The reason is picked here (Android shows at most 3 buttons), like the website's list.
    Alert.alert(
      t('requestService.cancelTitle', 'Cancel Service Request'),
      t('requestService.cancelWhy', 'Why are you cancelling? This cannot be undone.'),
      [
        { text: t('requestService.keepIt', 'Keep it'), style: 'cancel' },
        {
          text: t('requestService.cancelNoLongerNeeded', 'No longer needed'),
          style: 'destructive',
          onPress: () => confirmCancellation('no_longer_needed'),
        },
        {
          text: t('requestService.cancelOtherReason', 'Other reason'),
          style: 'destructive',
          onPress: () => confirmCancellation('other'),
        },
      ]
    );
  };

  const confirmCancellation = async (reasonType: string = 'other') => {
    try {
      setCanceling(true);
      await apiService.cancelServiceRequest(Number(id), reasonType);
      Alert.alert(t('common.success'), t('requestDetail.cancelledSuccess'), [
        { text: t('common.ok'), onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.response?.data?.error || t('requestDetail.failedCancel')
      );
    } finally {
      setCanceling(false);
    }
  };

  const handleMarkAsFinished = () => {
    Alert.alert(
      t('requestDetail.markFinished'),
      t('requestDetail.markFinishedConfirm'),
      [
        { text: t('assignments.notYet'), style: 'cancel' },
        {
          text: t('requestDetail.yesFinished'),
          onPress: confirmCompletion,
        },
      ]
    );
  };

  const confirmCompletion = async () => {
    try {
      setCompleting(true);
      await apiService.completeServiceRequest(Number(id));
      Alert.alert(t('common.success'), t('requestDetail.markedFinished'), [
        { text: t('common.ok'), onPress: () => loadRequestDetail() },
      ]);
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.response?.data?.error || t('requestDetail.failedMarkFinished')
      );
    } finally {
      setCompleting(false);
    }
  };

  const handleUploadScreenshot = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        t('paymentScreenshot.permissionRequired'),
        t('paymentScreenshot.galleryPermission')
      );
      return;
    }

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [3, 4],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        await uploadScreenshotToServer(result.assets[0]);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert(t('common.error'), t('paymentScreenshot.failedPickImage'));
    }
  };

  const uploadScreenshotToServer = async (screenshot: any) => {
    try {
      setUploadingScreenshot(true);

      const formData = new FormData();
      const localUri = screenshot.uri;
      const filename = localUri.split('/').pop() || 'payment_screenshot.jpg';
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : 'image/jpeg';

      formData.append('payment_screenshot', {
        uri: localUri,
        name: filename,
        type,
      } as any);

      await apiService.updateServiceRequest(Number(id), formData as any);

      Alert.alert(t('common.success'), t('requestDetail.screenshotUploaded'));
      await loadRequestDetail();
    } catch (error: any) {
      console.error('Error uploading screenshot:', error);
      Alert.alert(
        t('common.error'),
        error.response?.data?.error || t('requestDetail.failedUploadScreenshot')
      );
    } finally {
      setUploadingScreenshot(false);
    }
  };

  const getTimeSincePaid = () => {
    if (!request?.paid_at) return null;
    
    const paidTime = new Date(request.paid_at).getTime();
    const now = Date.now();
    const diffMinutes = Math.floor((now - paidTime) / (1000 * 60));
    
    return diffMinutes;
  };

  const showScreenshotUploadWarning = () => {
    const minutesSincePaid = getTimeSincePaid();
    if (minutesSincePaid === null) return false;
    
    // Show warning if payment is made but no screenshot and less than 7 minutes
    return !request?.payment_screenshot && minutesSincePaid < 7;
  };

  const getRemainingUploadTime = () => {
    const minutesSincePaid = getTimeSincePaid();
    if (minutesSincePaid === null) return 0;
    
    const remaining = 7 - minutesSincePaid;
    return Math.max(0, remaining);
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
    if (!dateString) return t('requestDetail.notAvailable');
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return t('requestDetail.invalidDate');
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch (error) {
      console.error('Error formatting date:', error);
      return t('requestDetail.invalidDate');
    }
  };

  const totalHours = useMemo(() => {
    if (!timeLogs || !Array.isArray(timeLogs) || timeLogs.length === 0) {
      console.log('📊 Total hours: 0 (no time logs)');
      return 0;
    }
    const total = timeLogs.reduce((sum, log) => {
      const hours = Number(log.duration_hours) || 0;
      return sum + hours;
    }, 0);
    const result = Number(total) || 0;
    console.log('📊 Total hours calculated:', result, 'from', timeLogs.length, 'logs');
    return result;
  }, [timeLogs]);

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title={t('requestDetail.title')} showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>
            {t('requestDetail.loading')}
          </Text>
        </View>
      </View>
    );
  }

  if (!request) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title={t('requestDetail.title')} showBack />
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={64} color={theme.textSecondary} />
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>
            {t('requestDetail.notFound')}
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
      <Header title={t('requestDetail.title')} showBack />

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
              {t(`status.${request.status}`, { defaultValue: request.status.replace('_', ' ') }).toUpperCase()}
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
              <Text style={[styles.editButtonText, { color: theme.primary }]}>{t('common.edit')}</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Request Details */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('requestDetail.title')}</Text>
          
          <View style={styles.detailRow}>
            <Ionicons name="document-text-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>{t('requestDetail.descriptionLabel')}</Text>
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
              {t('requestDetail.durationDays', { count: request.duration_days ?? 0, days: request.duration_days ?? '?' })}
              {request.duration_type_display ? ` (${request.duration_type_display})` : ''}
            </Text>
          </View>

          {request.preferred_date && (
            <View style={styles.detailRow}>
              <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailText, { color: theme.text }]}>
                {t('requestDetail.preferredDate', { date: new Date(request.preferred_date).toLocaleDateString() })}
                {request.preferred_time && t('requestDetail.atTime', { time: request.preferred_time })}
              </Text>
            </View>
          )}

          {request.client_notes && (
            <View style={styles.detailRow}>
              <Ionicons name="chatbox-ellipses-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>{t('requestDetail.clientNotes')}</Text>
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
              {t('requestDetail.urgency', {
                value: request.urgency ? t(`requestService.${request.urgency}`, { defaultValue: request.urgency }).toUpperCase() : '',
              })}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.detailText, { color: theme.textSecondary }]}>
              {t('requestDetail.requestedOn', { date: formatDateTime(request.created_at) })}
            </Text>
          </View>
        </View>

        {/* Payment Information */}
        {request.payment_method && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('requestDetail.paymentInfo')}</Text>
            
            <View style={styles.detailRow}>
              <Ionicons name="card-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailText, { color: theme.text }]}>
                {t('requestDetail.paymentMethod', { method: request.payment_method })}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <Ionicons name="receipt-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailText, { color: theme.text }]}>
                {t('requestDetail.transactionId', { id: request.payment_transaction_id })}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <Ionicons 
                name={request.payment_verified ? "checkmark-circle" : "time-outline"} 
                size={20} 
                color={request.payment_verified ? "#10b981" : "#f59e0b"} 
              />
              <Text style={[styles.detailText, { 
                color: request.payment_verified ? "#10b981" : "#f59e0b",
                fontFamily: 'Poppins_600SemiBold'
              }]}>
                {request.payment_verified ? t('requestDetail.paymentVerified') : t('requestDetail.verificationPending')}
              </Text>
            </View>

            {/* Screenshot Upload Section */}
            {!request.payment_screenshot ? (
              <View style={styles.uploadSection}>
                {showScreenshotUploadWarning() && (
                  <View style={styles.warningBox}>
                    <Ionicons name="warning" size={24} color="#dc2626" />
                    <View style={styles.warningTextContainer}>
                      <Text style={styles.warningTitle}>{t('requestDetail.proofRequired')}</Text>
                      <Text style={styles.warningText}>
                        {t('requestDetail.uploadWithin', { count: getRemainingUploadTime() })}
                      </Text>
                    </View>
                  </View>
                )}
                
                <TouchableOpacity
                  style={[styles.uploadButton, uploadingScreenshot && styles.uploadButtonDisabled]}
                  onPress={handleUploadScreenshot}
                  disabled={uploadingScreenshot}
                >
                  {uploadingScreenshot ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="cloud-upload-outline" size={24} color="#fff" />
                      <Text style={styles.uploadButtonText}>{t('requestDetail.uploadScreenshot')}</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.screenshotSection}>
                <Text style={[styles.detailLabel, { color: theme.textSecondary, marginBottom: 8 }]}>
                  {t('requestDetail.screenshotLabel')}
                </Text>
                <View style={styles.screenshotPreview}>
                  <Ionicons name="checkmark-circle" size={24} color="#10b981" />
                  <Text style={[styles.screenshotUploaded, { color: "#10b981" }]}>
                    {t('requestDetail.screenshotDone')}
                  </Text>
                </View>
              </View>
            )}
          </View>
        )}

        {/* Assigned Workers */}
        {request.assignments && Array.isArray(request.assignments) && request.assignments.length > 0 && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              {request.workers_needed && request.workers_needed > 1 
                ? t('requestDetail.assignedWorkers', { assigned: request.assignments.length, needed: request.workers_needed })
                : t('requestDetail.assignedWorker')}
            </Text>

            {/* Multiple Workers View - Only shows accepted workers */}
            {request.assignments && request.assignments.length > 0 ? (
              <>
                {request.assignments.map((assignment, index) => {
                  if (!assignment || !assignment.worker) return null;
                  return (
                  <View key={assignment.id} style={[styles.workerCard, index > 0 && styles.workerCardSpacing]}>
                    <View style={styles.workerHeader}>
                      {/* Worker Profile Picture or Avatar */}
                      {assignment.worker.profile_picture ? (
                        <TouchableOpacity 
                          onPress={() => {
                            setSelectedImage(assignment.worker.profile_picture || null);
                            setSelectedWorkerName(assignment.worker.full_name || t('messages.worker'));
                            setImageViewerVisible(true);
                          }}
                        >
                          <Image
                            source={{ uri: assignment.worker.profile_picture }}
                            style={[styles.avatar, styles.avatarImage]}
                          />
                        </TouchableOpacity>
                      ) : (
                        <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
                          <Text style={styles.avatarText}>
                            {assignment.worker.full_name?.charAt(0) || 'W'}
                          </Text>
                        </View>
                      )}
                      <View style={styles.workerInfo}>
                        <View style={styles.workerNameRow}>
                          <Text style={[styles.workerName, { color: theme.text }]}>
                            {assignment.worker.full_name || t('messages.worker')} 
                          </Text>
                          <Text style={[styles.assignmentNumber, { color: theme.textSecondary }]}>
                            #{assignment.assignment_number}
                          </Text>
                        </View>
                        {assignment.worker.rating != null && assignment.worker.rating > 0 && (
                          <View style={styles.ratingRow}>
                            <Ionicons name="star" size={16} color="#FFA500" />
                            <Text style={[styles.ratingText, { color: theme.textSecondary }]}>
                              {Number(assignment.worker.rating || 0).toFixed(1)}
                            </Text>
                          </View>
                        )}
                      </View>
                    </View>

                    {/* Assignment Status Badge */}
                    {assignment.status === 'accepted' && (
                      <View style={[styles.acceptedBadge, { backgroundColor: '#4CAF50' }]}>
                        <Ionicons name="checkmark-circle" size={16} color="#FFFFFF" />
                        <Text style={styles.acceptedText}>{t('assignments.accepted')}</Text>
                      </View>
                    )}

                    {assignment.status === 'in_progress' && (
                      <View style={[styles.inProgressBadge, { backgroundColor: '#9C27B0' }]}>
                        <Ionicons name="play-circle" size={16} color="#FFFFFF" />
                        <Text style={styles.inProgressText}>{t('assignments.inProgress')}</Text>
                      </View>
                    )}

                    {assignment.status === 'completed' && (
                      <View style={[styles.completedBadge, { backgroundColor: '#4CAF50' }]}>
                        <Ionicons name="checkmark-done-circle" size={16} color="#FFFFFF" />
                        <Text style={styles.completedText}>{t('favoriteWorkers.completedJobs')}</Text>
                      </View>
                    )}

                    {/* Contact Button for Accepted Workers */}
                    {assignment.status === 'accepted' || assignment.status === 'in_progress' ? (
                      <TouchableOpacity
                        style={[styles.callWorkerButton, { backgroundColor: theme.primary }]}
                        onPress={() => {
                          const phoneNumber = assignment.worker.phone_number;
                          if (phoneNumber) {
                            Linking.openURL(`tel:${phoneNumber}`);
                          } else {
                            Alert.alert(t('common.error'), t('requestDetail.phoneNotAvailable'));
                          }
                        }}
                      >
                        <Ionicons name="call" size={20} color="#FFFFFF" />
                        <Text style={styles.callWorkerButtonText}>{t('requestDetail.callWorker')}</Text>
                      </TouchableOpacity>
                    ) : null}
                    {/* Chat - the website had it, the app only offered a phone call */}
                    {(assignment.status === 'accepted' || assignment.status === 'in_progress' || assignment.status === 'completed')
                      && assignment.worker?.user_id ? (
                      <TouchableOpacity
                        style={[styles.callWorkerButton, { backgroundColor: theme.primary, opacity: 0.85, marginTop: 8 }]}
                        onPress={() => router.push(`/(client)/conversation/${assignment.worker.user_id}?name=${encodeURIComponent(assignment.worker.full_name || '')}` as any)}
                      >
                        <Ionicons name="chatbubbles" size={20} color="#FFFFFF" />
                        <Text style={styles.callWorkerButtonText}>{t('vacancies.chat')}</Text>
                      </TouchableOpacity>
                    ) : null}
                  </View>
                  );
                })}
              </>
            ) : (
              /* No workers assigned yet */
              <View style={styles.noWorkersContainer}>
                <Ionicons name="person-outline" size={48} color={theme.textSecondary} />
                <Text style={[styles.noWorkersText, { color: theme.textSecondary }]}>
                  {t('requestDetail.noWorkersYet')}
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Time Logs */}
        {timeLogs && Array.isArray(timeLogs) && timeLogs.length > 0 && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('requestDetail.timeTracking')}</Text>

            <View style={styles.summaryRow}>
              <Text style={[styles.summaryLabel, { color: theme.textSecondary }]}>
                {t('requestDetail.totalHours')}
              </Text>
              <Text style={[styles.summaryValue, { color: theme.primary }]}>
                {t('requestDetail.hoursShort', { hours: totalHours.toFixed(2) })}
              </Text>
            </View>

            <View style={styles.timeLogsList}>
              {timeLogs.map((log) => {
                if (!log || !log.id) return null;
                return (
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
                        {t('requestDetail.logDuration', { hours: Number(log.duration_hours || 0).toFixed(2) })}
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
                        {t('requestDetail.currentlyWorking')}
                      </Text>
                    </View>
                  )}
                </View>
                );
              })}
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
                  <Text style={styles.cancelButtonText}>{t('common.cancel')}</Text>
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
                  <Text style={styles.completeButtonText}>{t('requestDetail.markFinished')}</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Rate Worker Button */}
        {request.status === 'completed' && request.assignments && request.assignments.length > 0 && !request.client_rating && (
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[styles.rateButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push(`/(client)/rate-worker/${request.id}` as any)}
            >
              <Ionicons name="star-outline" size={20} color="#FFFFFF" />
              <Text style={styles.rateButtonText}>{t('requestDetail.rateService')}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Display Rating if already rated */}
        {request.status === 'completed' && request.client_rating && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('requestDetail.yourRating')}</Text>
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
      
      {/* Full-Screen Image Viewer Modal */}
      <Modal
        visible={imageViewerVisible}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setImageViewerVisible(false)}
      >
        <View style={styles.modalContainer}>
          <TouchableOpacity 
            style={styles.modalClose}
            onPress={() => setImageViewerVisible(false)}
            activeOpacity={0.9}
          >
            <Ionicons name="close-circle" size={40} color="#FFFFFF" />
          </TouchableOpacity>
          
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{selectedWorkerName}</Text>
            {selectedImage && (
              <Image
                source={{ uri: selectedImage }}
                style={styles.fullImage}
                resizeMode="contain"
              />
            )}
          </View>
        </View>
      </Modal>
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
    fontFamily: 'Poppins_700Bold',
  },
  title: {
    fontSize: 22,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 8,
  },
  category: {
    fontSize: 16,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_700Bold',
  },
  workerCard: {
    padding: 12,
  },
  workerCardSpacing: {
    marginTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 16,
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
  avatarImage: {
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2,
    borderColor: '#14b8a6',
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
  },
  workerInfo: {
    flex: 1,
  },
  workerNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  workerName: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  assignmentNumber: {
    fontSize: 14,
    fontFamily: 'Poppins_700Bold',
  },
  workerPayment: {
    fontSize: 13,
    marginTop: 2,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  ratingText: {
    fontSize: 14,
  },
  inProgressBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    gap: 6,
  },
  inProgressText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  completedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    gap: 6,
  },
  completedText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
  },
  rejectedBadge: {
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
  },
  rejectedText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_700Bold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
    fontFamily: 'Poppins_600SemiBold',
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
  uploadSection: {
    marginTop: 16,
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#fef2f2',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#dc2626',
  },
  warningTextContainer: {
    flex: 1,
    marginLeft: 12,
  },
  warningTitle: {
    fontSize: 14,
    fontFamily: 'Poppins_700Bold',
    color: '#dc2626',
    marginBottom: 4,
  },
  warningText: {
    fontSize: 13,
    color: '#991b1b',
    lineHeight: 18,
  },
  uploadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#14b8a6',
    padding: 16,
    borderRadius: 12,
    gap: 10,
  },
  uploadButtonText: {
    color: '#fff',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  uploadButtonDisabled: {
    backgroundColor: '#9ca3af',
  },
  screenshotSection: {
    marginTop: 16,
  },
  screenshotPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0fdf4',
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  screenshotUploaded: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  noWorkersContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  noWorkersText: {
    fontSize: 16,
    marginTop: 12,
    textAlign: 'center',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalClose: {
    position: 'absolute',
    top: 50,
    right: 20,
    zIndex: 10,
    padding: 10,
  },
  modalContent: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  fullImage: {
    width: '100%',
    height: '80%',
  },
});
