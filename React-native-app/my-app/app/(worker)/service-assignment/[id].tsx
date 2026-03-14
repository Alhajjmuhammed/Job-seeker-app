import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  TextInput,
  Linking,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import apiService from '../../../services/api';
import { useAuth } from '../../../contexts/AuthContext';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';

interface ServiceAssignmentDetail {
  id: number;
  title: string;
  description: string;
  category_name: string;
  urgency: 'normal' | 'urgent' | 'emergency';
  status: string;
  created_at: string;
  preferred_date: string | null;
  preferred_time: string | null;
  location: string;
  city: string;
  estimated_duration_hours: number;
  client_notes: string | null;
  worker_notes: string | null;
  rejection_reason: string | null;
  client_name: string;
  client_phone: string;
  client_email?: string;
  worker_accepted: boolean | null;
  work_started_at: string | null;
  work_completed_at: string | null;
}

interface TimeLog {
  id: number;
  clock_in: string;
  clock_out?: string;
  duration_hours?: number;
  clock_in_location?: string;
  clock_out_location?: string;
  notes?: string;
}

export default function ServiceAssignmentDetail() {
  const { id } = useLocalSearchParams();
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assignment, setAssignment] = useState<ServiceAssignmentDetail | null>(null);
  const [timeLogs, setTimeLogs] = useState<TimeLog[]>([]);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [notes, setNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  const loadAssignmentDetail = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.getWorkerAssignmentDetail(Number(id));
      
      // Extract assignment data from response
      const assignmentData = response.assignment || response.service_request || response;
      const clockedInStatus = response.is_clocked_in === true;
      
      // Update all states
      setAssignment(assignmentData);
      setTimeLogs(response.time_logs || []);
      setIsClockedIn(clockedInStatus);
      
      console.log('✅ Assignment Detail Loaded:', {
        assignmentId: assignmentData.id,
        status: assignmentData.status,
        workerAccepted: assignmentData.worker_accepted,
        isClockedIn: clockedInStatus,
        timeLogsCount: (response.time_logs || []).length
      });
    } catch (error: any) {
      console.error('❌ Error loading assignment:', error);
      Alert.alert('Error', error.response?.data?.error || 'Failed to load assignment details');
      router.back();
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAssignmentDetail();
  }, [loadAssignmentDetail]);

  // Reload data when screen comes back into focus (e.g., after clock in/out)
  useFocusEffect(
    React.useCallback(() => {
      console.log('🔄 Screen focused - Reloading assignment data...');
      loadAssignmentDetail();
      return () => {
        console.log('👋 Screen unfocused');
      };
    }, [loadAssignmentDetail])
  );

  const handleAccept = async () => {
    if (!assignment) return;

    Alert.alert(
      'Accept Assignment',
      'Are you sure you want to accept this service request?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Accept',
          onPress: async () => {
            try {
              setSubmitting(true);
              await apiService.acceptAssignment(assignment.id, notes || undefined);
              Alert.alert('Success', 'Assignment accepted successfully', [
                { text: 'OK', onPress: () => router.back() }
              ]);
            } catch (error: any) {
              console.error('Error accepting assignment:', error);
              const errorMessage = error.response?.data?.error || 'Failed to accept assignment';
              Alert.alert('Error', errorMessage);
            } finally {
              setSubmitting(false);
            }
          },
        },
      ]
    );
  };

  const handleReject = async () => {
    if (!assignment) return;
    
    if (!rejectionReason.trim()) {
      Alert.alert('Required', 'Please provide a reason for rejection');
      return;
    }

    Alert.alert(
      'Reject Assignment',
      'Are you sure you want to reject this service request?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reject',
          style: 'destructive',
          onPress: async () => {
            try {
              setSubmitting(true);
              await apiService.rejectAssignment(assignment.id, rejectionReason);
              Alert.alert('Rejected', 'Assignment rejected', [
                { text: 'OK', onPress: () => router.back() }
              ]);
            } catch (error: any) {
              console.error('Error rejecting assignment:', error);
              const errorMessage = error.response?.data?.error || 'Failed to reject assignment';
              Alert.alert('Error', errorMessage);
            } finally {
              setSubmitting(false);
            }
          },
        },
      ]
    );
  };

  const getUrgencyConfig = (urgency: string) => {
    const configs = {
      normal: { bg: '#e8f5e9', text: '#2e7d32', icon: 'checkmark-circle' },
      urgent: { bg: '#fff3e0', text: '#e65100', icon: 'warning' },
      emergency: { bg: '#ffebee', text: '#c62828', icon: 'alert-circle' },
    };
    return configs[urgency as keyof typeof configs] || configs.normal;
  };

  const getStatusBadge = (status: string) => {
    const colors: { [key: string]: { bg: string; text: string } } = {
      pending: { bg: '#fff3e0', text: '#e65100' },
      assigned: { bg: '#e3f2fd', text: '#1565c0' },
      in_progress: { bg: '#f3e5f5', text: '#6a1b9a' },
      completed: { bg: '#e8f5e9', text: '#2e7d32' },
      cancelled: { bg: '#fce4ec', text: '#c2185b' },
    };
    const config = colors[status] || { bg: '#f5f5f5', text: '#616161' };
    
    return (
      <View style={[styles.statusBadge, { backgroundColor: config.bg }]}>
        <Text style={[styles.statusText, { color: config.text }]}>
          {status.replace('_', ' ').toUpperCase()}
        </Text>
      </View>
    );
  };
  const handleCallClient = () => {
    if (assignment?.client_phone) {
      Linking.openURL(`tel:${assignment.client_phone}`);
    } else {
      Alert.alert('No Phone', 'Client phone number not available');
    }
  };

  const handleEmailClient = () => {
    if (assignment?.client_email) {
      Linking.openURL(`mailto:${assignment.client_email}`);
    } else {
      Alert.alert('No Email', 'Client email not available');
    }
  };
  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Assignment Details" showBack />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
        <StatusBar style={isDark ? 'light' : 'dark'} />
      </View>
    );
  }

  if (!assignment) {
    return null;
  }

  const urgencyConfig = getUrgencyConfig(assignment.urgency);
  // Can only respond if status is pending/assigned AND worker hasn't responded yet
  const canRespond = (assignment.status === 'pending' || assignment.status === 'assigned') && assignment.worker_accepted === null;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Assignment Details" showBack />
      
      <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
        {/* Header Card */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.cardHeader}>
            <Text style={[styles.title, { color: theme.text }]}>
              {assignment.title}
            </Text>
            {getStatusBadge(assignment.status)}
          </View>
          
          <View style={styles.categoryRow}>
            <Ionicons name="briefcase-outline" size={18} color={theme.textSecondary} />
            <Text style={[styles.categoryText, { color: theme.textSecondary }]}>
              {assignment.category_name}
            </Text>
          </View>

          <View style={[styles.urgencyCard, { backgroundColor: urgencyConfig.bg }]}>
            <Ionicons name={urgencyConfig.icon as any} size={24} color={urgencyConfig.text} />
            <Text style={[styles.urgencyTitle, { color: urgencyConfig.text }]}>
              {assignment.urgency.toUpperCase()} PRIORITY
            </Text>
          </View>
        </View>

        {/* Client Info */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Client Information</Text>
          
          <View style={styles.infoRow}>
            <Ionicons name="person-outline" size={20} color={theme.textSecondary} />
            <View style={styles.infoContent}>
              <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>Name</Text>
              <Text style={[styles.infoValue, { color: theme.text }]}>
                {assignment.client_name || 'N/A'}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="call-outline" size={20} color={theme.textSecondary} />
            <View style={styles.infoContent}>
              <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>Phone</Text>
              <Text style={[styles.infoValue, { color: theme.text }]}>
                {assignment.client_phone || 'N/A'}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="mail-outline" size={20} color={theme.textSecondary} />
            <View style={styles.infoContent}>
              <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>Email</Text>
              <Text style={[styles.infoValue, { color: theme.text }]}>
                {assignment.client_email || 'N/A'}
              </Text>
            </View>
          </View>

          {/* Contact Actions */}
          {(assignment.client_phone || assignment.client_email) && (
            <View style={styles.contactButtons}>
              {assignment.client_phone && (
                <TouchableOpacity
                  style={[styles.contactButton, { backgroundColor: theme.primary }]}
                  onPress={handleCallClient}
                >
                  <Ionicons name="call" size={20} color="#FFFFFF" />
                  <Text style={styles.contactButtonText}>Call Client</Text>
                </TouchableOpacity>
              )}
              {assignment.client_email && (
                <TouchableOpacity
                  style={[styles.contactButton, { backgroundColor: theme.primary, opacity: 0.8 }]}
                  onPress={handleEmailClient}
                >
                  <Ionicons name="mail" size={20} color="#FFFFFF" />
                  <Text style={styles.contactButtonText}>Email Client</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>

        {/* Service Details */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Service Details</Text>
          
          <Text style={[styles.description, { color: theme.textSecondary }]}>
            {assignment.description}
          </Text>

          <View style={styles.detailsGrid}>
            <View style={styles.detailItem}>
              <Ionicons name="location-outline" size={20} color={theme.textSecondary} />
              <View style={styles.detailContent}>
                <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                  Location
                </Text>
                <Text style={[styles.detailValue, { color: theme.text }]}>
                  {assignment.city}, {assignment.location}
                </Text>
              </View>
            </View>

            {assignment.preferred_date && (
              <View style={styles.detailItem}>
                <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
                <View style={styles.detailContent}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    Preferred Date
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.text }]}>
                    {new Date(assignment.preferred_date).toLocaleDateString()}
                  </Text>
                </View>
              </View>
            )}

            {assignment.preferred_time && (
              <View style={styles.detailItem}>
                <Ionicons name="time-outline" size={20} color={theme.textSecondary} />
                <View style={styles.detailContent}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    Preferred Time
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.text }]}>
                    {assignment.preferred_time}
                  </Text>
                </View>
              </View>
            )}

            <View style={styles.detailItem}>
              <Ionicons name="hourglass-outline" size={20} color={theme.textSecondary} />
              <View style={styles.detailContent}>
                <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                  Estimated Duration
                </Text>
                <Text style={[styles.detailValue, { color: theme.text }]}>
                  {assignment.estimated_duration_hours} hour{assignment.estimated_duration_hours !== 1 ? 's' : ''}
                </Text>
              </View>
            </View>
          </View>

          {assignment.client_notes && (
            <View style={styles.notesSection}>
              <Text style={[styles.notesLabel, { color: theme.textSecondary }]}>
                Client Notes:
              </Text>
              <Text style={[styles.notesText, { color: theme.text }]}>
                {assignment.client_notes}
              </Text>
            </View>
          )}
        </View>

        {/* Response Section (only for pending/assigned) */}
        {canRespond && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Your Response
            </Text>
            
            {!showRejectInput ? (
              <>
                <Text style={[styles.label, { color: theme.textSecondary }]}>
                  Notes (Optional)
                </Text>
                <TextInput
                  style={[
                    styles.textArea,
                    {
                      backgroundColor: theme.background,
                      color: theme.text,
                      borderColor: theme.border,
                    },
                  ]}
                  placeholder="Add any notes about this assignment..."
                  placeholderTextColor={theme.textSecondary}
                  value={notes}
                  onChangeText={setNotes}
                  multiline
                  numberOfLines={4}
                  textAlignVertical="top"
                />

                <View style={styles.actionButtons}>
                  <TouchableOpacity
                    style={[styles.acceptButton, { backgroundColor: theme.primary }]}
                    onPress={handleAccept}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="checkmark-circle" size={20} color="#fff" />
                        <Text style={styles.acceptButtonText}>Accept Assignment</Text>
                      </>
                    )}
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[styles.rejectButton, { borderColor: theme.error }]}
                    onPress={() => setShowRejectInput(true)}
                    disabled={submitting}
                  >
                    <Ionicons name="close-circle" size={20} color={theme.error} />
                    <Text style={[styles.rejectButtonText, { color: theme.error }]}>
                      Reject
                    </Text>
                  </TouchableOpacity>
                </View>
              </>
            ) : (
              <>
                <Text style={[styles.label, { color: theme.textSecondary }]}>
                  Rejection Reason *
                </Text>
                <TextInput
                  style={[
                    styles.textArea,
                    {
                      backgroundColor: theme.background,
                      color: theme.text,
                      borderColor: theme.border,
                    },
                  ]}
                  placeholder="Please explain why you're rejecting this assignment..."
                  placeholderTextColor={theme.textSecondary}
                  value={rejectionReason}
                  onChangeText={setRejectionReason}
                  multiline
                  numberOfLines={4}
                  textAlignVertical="top"
                  autoFocus
                />

                <View style={styles.actionButtons}>
                  <TouchableOpacity
                    style={[styles.rejectButton, { backgroundColor: theme.error }]}
                    onPress={handleReject}
                    disabled={submitting || !rejectionReason.trim()}
                  >
                    {submitting ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="close-circle" size={20} color="#fff" />
                        <Text style={styles.acceptButtonText}>Confirm Rejection</Text>
                      </>
                    )}
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[styles.cancelButton, { borderColor: theme.border }]}
                    onPress={() => {
                      setShowRejectInput(false);
                      setRejectionReason('');
                    }}
                    disabled={submitting}
                  >
                    <Text style={[styles.cancelButtonText, { color: theme.text }]}>
                      Cancel
                    </Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        )}

        {/* Action Buttons for Accepted/In Progress Assignments */}
        {(assignment.status === 'accepted' || assignment.status === 'in_progress') && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Actions
            </Text>

            {/* Debug Info - Remove in production */}
            <Text style={{ fontSize: 10, color: theme.textSecondary, marginBottom: 8 }}>
              Status: {isClockedIn ? 'Clocked In' : 'Clocked Out'} | Assignment: {assignment.status}
            </Text>

            {isClockedIn ? (
              // Show Clock Out button when clocked in
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: theme.error }]}
                onPress={() => {
                  console.log('🕐 Clock Out pressed - Assignment ID:', assignment.id, '| Clocked In:', isClockedIn);
                  router.push(`/(worker)/assignments/clock/out/${assignment.id}` as any);
                }}
              >
                <Ionicons name="log-out-outline" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>Clock Out</Text>
              </TouchableOpacity>
            ) : (
              // Show Clock In and Complete buttons when clocked out
              <>
                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: theme.primary }]}
                  onPress={() => {
                    console.log('🕐 Clock In pressed - Assignment ID:', assignment.id, '| Clocked In:', isClockedIn);
                    router.push(`/(worker)/assignments/clock/in/${assignment.id}` as any);
                  }}
                >
                  <Ionicons name="log-in-outline" size={20} color="#fff" />
                  <Text style={styles.actionButtonText}>Clock In</Text>
                </TouchableOpacity>

                {!isClockedIn && (
                  <TouchableOpacity
                    style={[styles.actionButton, { backgroundColor: theme.success || '#10b981', marginTop: 12 }]}
                    onPress={() => {
                      console.log('✅ Mark Complete pressed - Assignment ID:', assignment.id);
                      router.push(`/(worker)/assignments/complete/${assignment.id}` as any);
                    }}
                  >
                    <Ionicons name="checkmark-circle" size={20} color="#fff" />
                    <Text style={styles.actionButtonText}>Mark as Complete</Text>
                  </TouchableOpacity>
                )}
              </>
            )}
          </View>
        )}

        {/* Completed Status */}
        {assignment.status === 'completed' && (
          <View style={[styles.card, { backgroundColor: theme.success || '#10b981' }]}>
            <View style={styles.completedContent}>
              <Ionicons name="checkmark-circle" size={32} color="#fff" />
              <Text style={styles.completedText}>Service Completed!</Text>
              {assignment.work_completed_at && (
                <Text style={styles.completedDate}>
                  Completed on {new Date(assignment.work_completed_at).toLocaleDateString()}
                </Text>
              )}
            </View>
          </View>
        )}

        {/* Time Tracking - HIDDEN: Duration-based pricing, not hourly */}
        {/* Keeping this section commented for potential future use
        {(timeLogs.length > 0 || assignment.work_started_at) && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Time Tracking</Text>

            {isClockedIn && (
              <View style={[styles.timeRow, { backgroundColor: theme.primary + '15', borderRadius: 8, padding: 10, marginBottom: 8 }]}>
                <Ionicons name="timer-outline" size={18} color={theme.primary} />
                <Text style={[styles.timeValue, { color: theme.primary, marginLeft: 8 }]}>
                  ⏱️ Currently clocked in
                </Text>
              </View>
            )}

            {timeLogs.map((log) => (
              <View key={log.id} style={styles.timeRow}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.timeLabel, { color: theme.textSecondary }]}>
                    Clock In: {new Date(log.clock_in).toLocaleString()}
                  </Text>
                  {log.clock_out ? (
                    <>
                      <Text style={[styles.timeLabel, { color: theme.textSecondary }]}>
                        Clock Out: {new Date(log.clock_out).toLocaleString()}
                      </Text>
                      {log.duration_hours != null && (
                        <Text style={[styles.timeValue, { color: theme.primary }]}>
                          Duration: {Number(log.duration_hours).toFixed(2)} hrs
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text style={[styles.timeValue, { color: theme.primary }]}>Still in progress</Text>
                  )}
                  {log.notes ? (
                    <Text style={[styles.timeLabel, { color: theme.textSecondary }]}>
                      Notes: {log.notes}
                    </Text>
                  ) : null}
                </View>
              </View>
            ))}

            {timeLogs.length === 0 && assignment.work_started_at && (
              <View style={styles.timeRow}>
                <Text style={[styles.timeLabel, { color: theme.textSecondary }]}>
                  Work started: {new Date(assignment.work_started_at).toLocaleString()}
                </Text>
              </View>
            )}
          </View>
        )}
        */}
      </ScrollView>

      <StatusBar style={isDark ? 'light' : 'dark'} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  card: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    flex: 1,
    marginRight: 12,
  },
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  categoryText: {
    fontSize: 16,
  },
  urgencyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 8,
  },
  urgencyTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 16,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 16,
  },
  contactButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  contactButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  contactButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 16,
  },
  detailsGrid: {
    gap: 16,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  detailContent: {
    flex: 1,
  },
  detailLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 15,
  },
  notesSection: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  notesLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  notesText: {
    fontSize: 14,
    lineHeight: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    minHeight: 100,
    marginBottom: 16,
  },
  actionButtons: {
    gap: 12,
  },
  acceptButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 8,
  },
  acceptButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  rejectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 8,
    borderWidth: 2,
  },
  rejectButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  timeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  timeLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  timeValue: {
    fontSize: 14,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 8,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  completedContent: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  completedText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 12,
  },
  completedDate: {
    color: '#fff',
    fontSize: 14,
    marginTop: 8,
    opacity: 0.9,
  },
});
