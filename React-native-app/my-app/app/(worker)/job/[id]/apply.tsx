import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../../contexts/ThemeContext';
import Header from '../../../../components/Header';
import apiService from '../../../../services/api';

interface JobDetail {
  id: number;
  title: string;
  category: string;
  client: {
    name: string;
  };
  budget: number;
  duration: string;
}

export default function ApplyForJobScreen() {
  const { id } = useLocalSearchParams();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [job, setJob] = useState<JobDetail | null>(null);
  
  // Form fields
  const [coverLetter, setCoverLetter] = useState('');
  const [proposedRate, setProposedRate] = useState('');

  useEffect(() => {
    loadJobDetail();
  }, []);

  const loadJobDetail = async () => {
    try {
      setLoading(true);
      const jobData = await apiService.getJobDetail(Number(id));
      setJob(jobData);
    } catch (error) {
      console.error('Error loading job:', error);
      Alert.alert('Error', 'Failed to load job details', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (coverLetter.trim().length < 50) {
      Alert.alert('Validation Error', 'Please write a cover letter with at least 50 characters to stand out');
      return;
    }

    if (proposedRate && (isNaN(parseFloat(proposedRate)) || parseFloat(proposedRate) <= 0)) {
      Alert.alert('Validation Error', 'Please enter a valid hourly rate');
      return;
    }

    try {
      setSubmitting(true);
      await apiService.applyForJob(
        Number(id),
        coverLetter,
        proposedRate ? parseFloat(proposedRate) : undefined
      );
      
      Alert.alert(
        'Success',
        'Your application has been submitted successfully!',
        [
          {
            text: 'OK',
            onPress: () => {
              // Go back twice to return to jobs list
              router.back();
              router.back();
            }
          }
        ]
      );
    } catch (error: any) {
      console.error('Failed to apply:', error);
      Alert.alert('Error', error.response?.data?.error || 'Failed to submit application');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header showBack />
        <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading job details...</Text>
        </View>
      </View>
    );
  }

  if (!job) {
    return null;
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <StatusBar style={theme.statusBar} />
      <Header showBack />

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.text }]}>Apply for Job</Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
            Make a great impression with your application
          </Text>
        </View>

        {/* Job Preview */}
        <View style={[styles.jobPreview, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.jobPreviewHeader}>
            <Ionicons name="briefcase" size={24} color={theme.primary} />
            <View style={styles.jobPreviewText}>
              <Text style={[styles.jobTitle, { color: theme.text }]}>{job.title}</Text>
              <Text style={[styles.jobClient, { color: theme.textSecondary }]}>
                {job.client.name} • {job.category}
              </Text>
            </View>
          </View>
          <View style={styles.jobMeta}>
            <View style={styles.metaItem}>
              <Ionicons name="cash-outline" size={16} color={theme.primary} />
              <Text style={[styles.metaText, { color: theme.text }]}>
                ${job.budget}/{job.duration}
              </Text>
            </View>
          </View>
        </View>

        {/* Cover Letter */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="document-text" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>
                Cover Letter <Text style={styles.required}>*</Text>
              </Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>
                Why are you a good fit for this job?
              </Text>
            </View>
          </View>

          <TextInput
            style={[styles.textArea, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
            value={coverLetter}
            onChangeText={setCoverLetter}
            placeholder="Introduce yourself and explain why you're perfect for this job. Highlight your relevant experience, skills, and what value you can bring..."
            placeholderTextColor={theme.textSecondary}
            multiline
            numberOfLines={10}
            textAlignVertical="top"
          />
          
          <View style={styles.characterCount}>
            <Ionicons 
              name={coverLetter.length >= 50 ? "checkmark-circle" : "alert-circle"} 
              size={16} 
              color={coverLetter.length >= 50 ? '#10B981' : theme.textSecondary} 
            />
            <Text style={[styles.characterCountText, { color: coverLetter.length >= 50 ? '#10B981' : theme.textSecondary }]}>
              {coverLetter.length} characters (minimum 50)
            </Text>
          </View>

          <View style={[styles.tipCard, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.1)' : '#EFF6FF' }]}>
            <Ionicons name="bulb" size={20} color="#3B82F6" />
            <Text style={[styles.tipText, { color: isDark ? '#93C5FD' : '#1E40AF' }]}>
              <Text style={{ fontFamily: 'Poppins_600SemiBold' }}>Tip:</Text> Include specific examples of similar work you've done and explain how your skills match the job requirements.
            </Text>
          </View>
        </View>

        {/* Proposed Rate */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="cash" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>
                Your Rate (Optional)
              </Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>
                Propose your hourly rate in USD
              </Text>
            </View>
          </View>

          <View style={styles.inputWithPrefix}>
            <Text style={[styles.inputPrefix, { color: theme.textSecondary }]}>$</Text>
            <TextInput
              style={[styles.rateInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
              value={proposedRate}
              onChangeText={setProposedRate}
              placeholder="0.00"
              placeholderTextColor={theme.textSecondary}
              keyboardType="decimal-pad"
            />
            <Text style={[styles.inputSuffix, { color: theme.textSecondary }]}>/hour</Text>
          </View>

          <Text style={[styles.helpText, { color: theme.textSecondary }]}>
            Leave blank to use your profile rate (${job.budget || '0.00'}/hour)
          </Text>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            { backgroundColor: theme.primary },
            (submitting || coverLetter.length < 50) && styles.disabledButton
          ]}
          onPress={handleSubmit}
          disabled={submitting || coverLetter.length < 50}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="paper-plane" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>Submit Application</Text>
            </>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.cancelButton, { borderColor: theme.border }]}
          onPress={() => router.back()}
          disabled={submitting}
        >
          <Text style={[styles.cancelButtonText, { color: theme.textSecondary }]}>Cancel</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
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
    fontFamily: 'Poppins_400Regular',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  jobPreview: {
    padding: 20,
    borderRadius: 16,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  jobPreviewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  jobPreviewText: {
    flex: 1,
  },
  jobTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 2,
  },
  jobClient: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  jobMeta: {
    flexDirection: 'row',
    gap: 16,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  section: {
    padding: 20,
    borderRadius: 16,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  sectionTitleContainer: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
  },
  sectionSubtitle: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    marginTop: 2,
  },
  required: {
    color: '#EF4444',
  },
  textArea: {
    minHeight: 160,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 24,
  },
  characterCount: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  characterCountText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  tipCard: {
    flexDirection: 'row',
    gap: 12,
    padding: 12,
    borderRadius: 12,
    marginTop: 12,
  },
  tipText: {
    flex: 1,
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
  },
  inputWithPrefix: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  inputPrefix: {
    fontSize: 20,
    fontFamily: 'Poppins_600SemiBold',
    marginRight: 8,
  },
  rateInput: {
    flex: 1,
    height: 56,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
  },
  inputSuffix: {
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    marginLeft: 8,
  },
  helpText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 56,
    borderRadius: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  disabledButton: {
    opacity: 0.5,
  },
  cancelButton: {
    height: 56,
    borderRadius: 16,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
});
