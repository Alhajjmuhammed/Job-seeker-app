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
  Image,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../../contexts/ThemeContext';
import Header from '../../../../components/Header';
import apiService from '../../../../services/api';
import { useTranslation } from 'react-i18next';

interface Assignment {
  id: number;
  title: string;
  description: string;
  category_name: string;
  location: string;
  city: string;
  client_name: string;
  total_price?: number;
}

export default function CompleteServiceScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [completionNotes, setCompletionNotes] = useState('');

  useEffect(() => {
    loadAssignment();
  }, [id]);

  const loadAssignment = async () => {
    try {
      setLoading(true);
      const response = await apiService.getWorkerAssignmentDetail(Number(id));
      const assignmentData = response.assignment || response;
      
      // Check if assignment is already completed
      if (assignmentData.status === 'completed') {
        Alert.alert(
          t('assignments.alreadyCompleted'),
          t('assignments.alreadyCompletedMsg'),
          [
            {
              text: t('common.ok'),
              onPress: () => {
                router.replace(`/(worker)/service-assignment/${id}` as any);
              }
            }
          ]
        );
        return;
      }
      
      setAssignment(assignmentData);
    } catch (error: any) {
      console.error('Error loading assignment:', error);
      Alert.alert(t('common.error'), t('assignments.failedLoadAssignments'));
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!assignment) return;

    if (!completionNotes.trim()) {
      Alert.alert(
        t('assignments.completionNotesRequired'),
        t('assignments.provideCompletionNotes')
      );
      return;
    }

    Alert.alert(
      t('assignments.completeService'),
      t('assignments.markAsComplete'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('assignments.yesComplete'),
          onPress: confirmComplete,
        },
      ]
    );
  };

  const confirmComplete = async () => {
    if (!assignment) return;

    try {
      setSubmitting(true);
      console.log('✅ Marking Complete:', {
        assignmentId: assignment.id,
        hasNotes: !!completionNotes.trim()
      });
      
      const result = await apiService.completeService(assignment.id, completionNotes);
      console.log('✅ Complete Success:', result);
      
      // Navigate back with a slight delay to ensure state updates
      setTimeout(() => {
        router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
      }, 300);
      
      Alert.alert(
        t('assignments.serviceCompletedSuccess'),
        t('assignments.excellentWork')
      );
    } catch (error: any) {
      const errorData = error.response?.data?.error || error.message || '';
      
      // Check if assignment is already completed (expected case - not a real error)
      if (errorData.toLowerCase().includes('already completed')) {
        console.log('ℹ️ Assignment already completed, redirecting back');
        Alert.alert(
          t('assignments.alreadyCompleted'),
          t('assignments.alreadyCompletedMsg'),
          [
            {
              text: t('common.ok'),
              onPress: () => {
                router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
              }
            }
          ]
        );
      } else {
        console.log('❌ Complete Error:', {
          error: error.message,
          response: error.response?.data,
          status: error.response?.status
        });
        const errorMessage = error.response?.data?.error || error.message || t('assignments.failedCompleteService');
        Alert.alert(t('assignments.completeFailed'), errorMessage);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title={t('assignments.completeService')} showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>{t('requestService.loading')}</Text>
        </View>
      </View>
    );
  }

  if (!assignment) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title={t('assignments.completeService')} showBack />
        <View style={styles.errorContainer}>
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>
            {t('assignments.assignmentNotFound')}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title={t('assignments.completeService')} showBack />

      <ScrollView style={styles.content}>
        {/* Success Banner */}
        <View style={[styles.banner, { backgroundColor: '#4CAF50' }]}>
          <Ionicons name="checkmark-circle" size={64} color="#FFFFFF" />
          <Text style={styles.bannerTitle}>{t('assignments.readyToComplete')}</Text>
          <Text style={styles.bannerSubtitle}>
            {t('assignments.markAsFinished')}
          </Text>
        </View>

        {/* Assignment Summary */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            {t('assignments.serviceSummary')}
          </Text>
          
          <Text style={[styles.title, { color: theme.text }]}>
            {assignment.title}
          </Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {assignment.category_name}
          </Text>

          <View style={styles.divider} />

          <Text style={[styles.description, { color: theme.text }]}>
            {assignment.description}
          </Text>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <Ionicons name="location-outline" size={18} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              {assignment.city}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="person-outline" size={18} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              Client: {assignment.client_name}
            </Text>
          </View>

          {assignment.total_price && (
            <View style={styles.infoRow}>
              <Ionicons name="cash-outline" size={18} color={theme.primary} />
              <Text style={[styles.budgetText, { color: theme.primary }]}>
                TSH {assignment.total_price.toFixed(2)}
              </Text>
            </View>
          )}
        </View>

        {/* Completion Notes */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            {t('assignments.completionNotes')}
          </Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>{t('assignments.describeWorkCompleted')}</Text>

          <TextInput
            style={[
              styles.textArea,
              { backgroundColor: theme.background, color: theme.text },
            ]}
            placeholder={t('assignments.completed')}
            placeholderTextColor={theme.textSecondary}
            value={completionNotes}
            onChangeText={setCompletionNotes}
            multiline
            numberOfLines={8}
          />

          <View style={[styles.tipsBox, { backgroundColor: '#E3F2FD' }]}>
            <Ionicons name="bulb-outline" size={20} color="#2196F3" />
            <View style={styles.tipsContent}>
              <Text style={styles.tipsTitle}>{t('assignments.whatToInclude')}</Text>
              <Text style={styles.tipText}>{t('assignments.materialsUsed')}</Text>
              <Text style={styles.tipText}>{t('assignments.issuesResolved')}</Text>
              <Text style={styles.tipText}>{t('assignments.maintenanceRecommendations')}</Text>
              <Text style={styles.tipText}>{t('assignments.followUpActions')}</Text>
            </View>
          </View>
        </View>

        {/* Completion Checklist */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            {t('assignments.completionChecklist')}
          </Text>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>{t('assignments.workCompleted')}</Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              {t('assignments.qualityChecked')}
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              {t('assignments.areaClean')}
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              {t('assignments.clientSatisfied')}
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              {t('assignments.notesDocumented')}
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              {t('assignments.photosTaken')}
            </Text>
          </View>
        </View>

        {/* Important Notice */}
        <View style={[styles.noticeBox, { backgroundColor: '#FFF3CD' }]}>
          <Ionicons name="warning" size={24} color="#856404" />
          <View style={styles.noticeContent}>
            <Text style={styles.noticeTitle}>{t('assignments.important')}</Text>
            <Text style={styles.noticeText}>
              {t('assignments.ensureClientSatisfied')}
            </Text>
            <Text style={styles.noticeText}>
              {t('assignments.actionCannotUndo')}
            </Text>
            <Text style={styles.noticeText}>
              {t('assignments.clientNotified')}
            </Text>
            <Text style={styles.noticeText}>
              {t('assignments.paymentProcessed')}
            </Text>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actionContainer}>
          <TouchableOpacity
            style={[styles.completeButton, { backgroundColor: '#4CAF50' }]}
            onPress={handleComplete}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="checkmark-done" size={28} color="#FFFFFF" />
                <Text style={styles.completeButtonText}>{t('assignments.markComplete')}</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.cancelButton, { borderColor: theme.border }]}
            onPress={() => router.back()}
          >
            <Text style={[styles.cancelButtonText, { color: theme.text }]}>
              {t('assignments.notYet')}
            </Text>
          </TouchableOpacity>
        </View>
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
  banner: {
    alignItems: 'center',
    padding: 32,
  },
  bannerTitle: {
    color: '#FFFFFF',
    fontSize: 28,
    fontWeight: '700',
    marginTop: 16,
  },
  bannerSubtitle: {
    color: '#FFFFFF',
    fontSize: 16,
    marginTop: 8,
  },
  card: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 4,
  },
  category: {
    fontSize: 14,
    marginBottom: 12,
  },
  divider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 12,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  infoText: {
    fontSize: 14,
  },
  budgetText: {
    fontSize: 16,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 14,
    marginBottom: 12,
  },
  textArea: {
    padding: 12,
    borderRadius: 8,
    fontSize: 14,
    minHeight: 150,
    textAlignVertical: 'top',
    marginBottom: 12,
  },
  tipsBox: {
    flexDirection: 'row',
    padding: 12,
    borderRadius: 8,
    gap: 10,
  },
  tipsContent: {
    flex: 1,
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#2196F3',
    marginBottom: 6,
  },
  tipText: {
    fontSize: 12,
    color: '#1976D2',
    marginBottom: 2,
  },
  checklistItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  checklistText: {
    fontSize: 14,
    flex: 1,
  },
  noticeBox: {
    flexDirection: 'row',
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  noticeContent: {
    flex: 1,
  },
  noticeTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#856404',
    marginBottom: 8,
  },
  noticeText: {
    fontSize: 12,
    color: '#856404',
    marginBottom: 4,
  },
  actionContainer: {
    padding: 16,
  },
  completeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 18,
    borderRadius: 12,
    marginBottom: 12,
    gap: 10,
  },
  completeButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
  },
  cancelButton: {
    padding: 14,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});
