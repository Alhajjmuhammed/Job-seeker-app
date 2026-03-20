import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../../contexts/ThemeContext';
import Header from '../../../../components/Header';
import apiService from '../../../../services/api';
import { useTranslation } from 'react-i18next';

interface AssignmentDetail {
  id: number;
  title: string;
  description: string;
  category_name: string;
  urgency: string;
  location: string;
  city: string;
  total_price?: number;
  duration_days: number;
  created_at: string;
  assigned_at: string;
  client_name: string;
}

export default function RespondAssignmentScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null);
  const [action, setAction] = useState<'accept' | 'reject' | null>(null);
  const [notes, setNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  useEffect(() => {
    loadAssignment();
  }, [id]);

  const loadAssignment = async () => {
    try {
      setLoading(true);
      // Get from pending assignments list
      const response = await apiService.getPendingAssignments();
      const assignments = response.results || response;
      const found = assignments.find((a: any) => a.id === Number(id));
      if (found) {
        setAssignment(found);
      } else {
        Alert.alert(t('common.error'), t('assignments.assignmentNotFound'));
        router.back();
      }
    } catch (error: any) {
      console.error('Error loading assignment:', error);
      Alert.alert(t('common.error'), t('assignments.failedLoadAssignmentDetails'));
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!assignment) return;

    try {
      setSubmitting(true);
      await apiService.acceptAssignment(assignment.id, notes);
      Alert.alert(
        t('assignments.assignmentAccepted'),
        t('assignments.acceptedSuccessMsg'),
        [
          {
            text: t('assignments.viewAssignment'),
            onPress: () => router.replace('/(worker)/dashboard'),
          },
        ]
      );
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.response?.data?.error || t('assignments.failedAcceptAssignment')
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!assignment) return;

    if (!rejectionReason.trim()) {
      Alert.alert(t('assignments.reasonRequired'), t('assignments.provideReasonRejection'));
      return;
    }

    Alert.alert(
      t('assignments.confirmRejection'),
      t('assignments.sureRejectAssignment'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('assignments.yesReject'),
          style: 'destructive',
          onPress: confirmReject,
        },
      ]
    );
  };

  const confirmReject = async () => {
    if (!assignment) return;

    try {
      setSubmitting(true);
      await apiService.rejectAssignment(assignment.id, rejectionReason);
      Alert.alert(
        t('assignments.assignmentRejected'),
        t('assignments.rejectedAdminNotified'),
        [{ text: t('common.ok'), onPress: () => router.replace('/(worker)/dashboard') }]
      );
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.response?.data?.error || t('assignments.failedRejectAssignment')
      );
    } finally {
      setSubmitting(false);
    }
  };

  const getUrgencyColor = (urgency: string) => {
    const colors = {
      low: '#4CAF50',
      medium: '#FFA500',
      high: '#F44336',
      urgent: '#D32F2F',
    };
    return colors[urgency as keyof typeof colors] || theme.textSecondary;
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Respond to Assignment" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>
            Loading assignment...
          </Text>
        </View>
      </View>
    );
  }

  if (!assignment) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Respond to Assignment" showBack />
        <View style={styles.errorContainer}>
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>
            Assignment not found
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Respond to Assignment" showBack />

      <ScrollView style={styles.content}>
        {/* Urgency Banner */}
        <View
          style={[
            styles.urgencyBanner,
            { backgroundColor: getUrgencyColor(assignment.urgency) },
          ]}
        >
          <Ionicons name="flag" size={24} color="#FFFFFF" />
          <Text style={styles.urgencyText}>
            {assignment.urgency.toUpperCase()} PRIORITY
          </Text>
        </View>

        {/* Assignment Details Card */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.title, { color: theme.text }]}>
            {assignment.title}
          </Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {assignment.category_name}
          </Text>

          <View style={styles.divider} />

          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Description
          </Text>
          <Text style={[styles.description, { color: theme.text }]}>
            {assignment.description}
          </Text>

          <View style={styles.divider} />

          {/* Details Grid */}
          <View style={styles.detailsGrid}>
            <View style={styles.detailItem}>
              <Ionicons name="location-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>{t('jobs.location')}</Text>
              <Text style={[styles.detailValue, { color: theme.text }]}>
                {assignment.city}
              </Text>
            </View>

            <View style={styles.detailItem}>
              <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                Duration
              </Text>
              <Text style={[styles.detailValue, { color: theme.text }]}>
                {assignment.duration_days} days
              </Text>
            </View>

            {assignment.total_price && (
              <View style={styles.detailItem}>
                <Ionicons name="cash-outline" size={20} color={theme.primary} />
                <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                  Total Price
                </Text>
                <Text style={[styles.budgetValue, { color: theme.primary }]}>
                  TSH {assignment.total_price.toFixed(2)}
                </Text>
              </View>
            )}

            <View style={styles.detailItem}>
              <Ionicons name="time-outline" size={20} color={theme.textSecondary} />
              <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>{t('assignments.assigned')}</Text>
              <Text style={[styles.detailValue, { color: theme.text }]}>
                {formatDateTime(assignment.assigned_at)}
              </Text>
            </View>
          </View>
        </View>

        {/* Client Information */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            {t('assignments.clientInformation')}
          </Text>
          <View style={[styles.clientCard, { backgroundColor: theme.background }]}>
            <View style={[styles.clientAvatar, { backgroundColor: theme.primary }]}>
              <Text style={styles.clientInitial}>
                {assignment.client_name.charAt(0)}
              </Text>
            </View>
            <View style={styles.clientInfo}>
              <Text style={[styles.clientName, { color: theme.text }]}>
                {assignment.client_name}
              </Text>
            </View>
          </View>
        </View>

        {/* Response Action Selection */}
        {!action && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              {t('assignments.yourResponse')}
            </Text>
            <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
              {t('assignments.reviewDetailsBeforeResponding')}
            </Text>

            <TouchableOpacity
              style={[styles.actionButton, styles.acceptButton]}
              onPress={() => setAction('accept')}
            >
              <Ionicons name="checkmark-circle" size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>{t('assignments.acceptAssignment')}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.rejectButton]}
              onPress={() => setAction('reject')}
            >
              <Ionicons name="close-circle" size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>{t('assignments.rejectAssignment')}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Accept Form */}
        {action === 'accept' && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <View style={styles.formHeader}>
              <Ionicons name="checkmark-circle" size={28} color="#4CAF50" />
              <Text style={[styles.formTitle, { color: theme.text }]}>
                {t('assignments.acceptingAssignment')}
              </Text>
            </View>

            <Text style={[styles.formSubtitle, { color: theme.textSecondary }]}>
              {t('assignments.addNotesForClient')}
            </Text>

            <TextInput
              style={[
                styles.textArea,
                { backgroundColor: theme.background, color: theme.text },
              ]}
              placeholder={t('assignments.exampleArrivalTime')}
              placeholderTextColor={theme.textSecondary}
              value={notes}
              onChangeText={setNotes}
              multiline
              numberOfLines={4}
            />

            <View style={styles.buttonRow}>
              <TouchableOpacity
                style={[styles.secondaryButton, { borderColor: theme.border }]}
                onPress={() => setAction(null)}
              >
                <Text style={[styles.secondaryButtonText, { color: theme.text }]}>{t('common.back')}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.primaryButton, { backgroundColor: '#4CAF50' }]}
                onPress={handleAccept}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#FFFFFF" />
                ) : (
                  <>
                    <Ionicons name="checkmark" size={20} color="#FFFFFF" />
                    <Text style={styles.primaryButtonText}>{t('common.confirm')}</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Reject Form */}
        {action === 'reject' && (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <View style={styles.formHeader}>
              <Ionicons name="close-circle" size={28} color="#F44336" />
              <Text style={[styles.formTitle, { color: theme.text }]}>
                {t('assignments.rejectingAssignment')}
              </Text>
            </View>

            <Text style={[styles.formSubtitle, { color: theme.textSecondary }]}>
              {t('assignments.provideRejectionReasonRequired')}
            </Text>

            <TextInput
              style={[
                styles.textArea,
                { backgroundColor: theme.background, color: theme.text },
              ]}
              placeholder={t('assignments.exampleRejectionReason')}
              placeholderTextColor={theme.textSecondary}
              value={rejectionReason}
              onChangeText={setRejectionReason}
              multiline
              numberOfLines={4}
            />

            <View style={styles.warningBox}>
              <Ionicons name="warning-outline" size={20} color="#FFA500" />
              <Text style={styles.warningText}>
                {t('assignments.rejectWarning')}
              </Text>
            </View>

            <View style={styles.buttonRow}>
              <TouchableOpacity
                style={[styles.secondaryButton, { borderColor: theme.border }]}
                onPress={() => setAction(null)}
              >
                <Text style={[styles.secondaryButtonText, { color: theme.text }]}>{t('common.back')}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.primaryButton, { backgroundColor: '#F44336' }]}
                onPress={handleReject}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#FFFFFF" />
                ) : (
                  <>
                    <Ionicons name="close" size={20} color="#FFFFFF" />
                    <Text style={styles.primaryButtonText}>{t('common.confirm')}</Text>
                  </>
                )}
              </TouchableOpacity>
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
  },
  content: {
    flex: 1,
  },
  urgencyBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 8,
  },
  urgencyText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  card: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 4,
  },
  category: {
    fontSize: 16,
    marginBottom: 16,
  },
  divider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
  },
  detailsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
  },
  detailItem: {
    width: '50%',
    marginBottom: 16,
  },
  detailLabel: {
    fontSize: 12,
    marginTop: 4,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    marginTop: 2,
  },
  budgetValue: {
    fontSize: 16,
    fontWeight: '700',
    marginTop: 2,
  },
  clientCard: {
    flexDirection: 'row',
    padding: 12,
    borderRadius: 8,
  },
  clientAvatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  clientInitial: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '700',
  },
  clientInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  clientName: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },
  contactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  contactText: {
    fontSize: 12,
  },
  subtitle: {
    fontSize: 14,
    marginBottom: 16,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
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
    fontWeight: '600',
  },
  formHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  formSubtitle: {
    fontSize: 14,
    marginBottom: 12,
  },
  textArea: {
    padding: 12,
    borderRadius: 8,
    fontSize: 14,
    minHeight: 100,
    textAlignVertical: 'top',
    marginBottom: 16,
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#FFF3CD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  warningText: {
    flex: 1,
    color: '#856404',
    fontSize: 12,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
  },
  secondaryButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  primaryButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
    borderRadius: 8,
    gap: 6,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
