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
      const response = await apiService.getCurrentAssignment();
      if (response.service_request && response.service_request.id === Number(id)) {
        setAssignment(response.service_request);
      }
    } catch (error: any) {
      console.error('Error loading assignment:', error);
      Alert.alert('Error', 'Failed to load assignment');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!assignment) return;

    if (!completionNotes.trim()) {
      Alert.alert(
        'Completion Notes Required',
        'Please provide notes about the completed work. This helps the client understand what was done.'
      );
      return;
    }

    Alert.alert(
      'Complete Service',
      'Are you sure you want to mark this service as complete? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Yes, Complete',
          onPress: confirmComplete,
        },
      ]
    );
  };

  const confirmComplete = async () => {
    if (!assignment) return;

    try {
      setSubmitting(true);
      await apiService.completeService(assignment.id, completionNotes);
      
      Alert.alert(
        '🎉 Service Completed!',
        'Excellent work! The service has been marked as complete. The client will be notified.',
        [
          {
            text: 'View Dashboard',
            onPress: () => router.replace('/(worker)/dashboard'),
          },
        ]
      );
    } catch (error: any) {
      Alert.alert(
        'Error',
        error.response?.data?.error || 'Failed to complete service. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Complete Service" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>
            Loading...
          </Text>
        </View>
      </View>
    );
  }

  if (!assignment) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Complete Service" showBack />
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
      <Header title="Complete Service" showBack />

      <ScrollView style={styles.content}>
        {/* Success Banner */}
        <View style={[styles.banner, { backgroundColor: '#4CAF50' }]}>
          <Ionicons name="checkmark-circle" size={64} color="#FFFFFF" />
          <Text style={styles.bannerTitle}>Ready to Complete!</Text>
          <Text style={styles.bannerSubtitle}>
            Mark this service as finished
          </Text>
        </View>

        {/* Assignment Summary */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Service Summary
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
            Completion Notes *
          </Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
            Describe what was completed, any issues encountered, and recommendations
          </Text>

          <TextInput
            style={[
              styles.textArea,
              { backgroundColor: theme.background, color: theme.text },
            ]}
            placeholder="Example:&#10;• Completed all plumbing repairs&#10;• Replaced kitchen faucet with new model&#10;• Fixed leaky pipe under sink&#10;• Cleaned work area thoroughly&#10;• Recommend annual maintenance check"
            placeholderTextColor={theme.textSecondary}
            value={completionNotes}
            onChangeText={setCompletionNotes}
            multiline
            numberOfLines={8}
          />

          <View style={[styles.tipsBox, { backgroundColor: '#E3F2FD' }]}>
            <Ionicons name="bulb-outline" size={20} color="#2196F3" />
            <View style={styles.tipsContent}>
              <Text style={styles.tipsTitle}>What to Include:</Text>
              <Text style={styles.tipText}>✓ All completed tasks</Text>
              <Text style={styles.tipText}>✓ Materials used</Text>
              <Text style={styles.tipText}>✓ Any issues resolved</Text>
              <Text style={styles.tipText}>✓ Maintenance recommendations</Text>
              <Text style={styles.tipText}>✓ Follow-up actions needed</Text>
            </View>
          </View>
        </View>

        {/* Completion Checklist */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Completion Checklist
          </Text>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              All work completed as requested
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              Quality checked and verified
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              Work area cleaned
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              Client satisfied with results
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              Completion notes documented
            </Text>
          </View>

          <View style={styles.checklistItem}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={[styles.checklistText, { color: theme.text }]}>
              Photos taken (if applicable)
            </Text>
          </View>
        </View>

        {/* Important Notice */}
        <View style={[styles.noticeBox, { backgroundColor: '#FFF3CD' }]}>
          <Ionicons name="warning" size={24} color="#856404" />
          <View style={styles.noticeContent}>
            <Text style={styles.noticeTitle}>Important</Text>
            <Text style={styles.noticeText}>
              • Make sure client is satisfied before marking complete
            </Text>
            <Text style={styles.noticeText}>
              • This action cannot be undone
            </Text>
            <Text style={styles.noticeText}>
              • Client will be notified immediately
            </Text>
            <Text style={styles.noticeText}>
              • Payment will be processed after client confirmation
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
                <Text style={styles.completeButtonText}>
                  Mark as Complete
                </Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.cancelButton, { borderColor: theme.border }]}
            onPress={() => router.back()}
          >
            <Text style={[styles.cancelButtonText, { color: theme.text }]}>
              Not Yet
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
