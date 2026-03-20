import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import StarRating from '../../../components/StarRating';
import apiService from '../../../services/api';
import { useTranslation } from 'react-i18next';

export default function RateWorkerScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams(); // service request id
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [request, setRequest] = useState<any>(null);
  const [rating, setRating] = useState(0);
  const [review, setReview] = useState('');

  useEffect(() => {
    loadRequestDetails();
  }, [id]);

  const loadRequestDetails = async () => {
    try {
      setLoading(true);
      const response = await apiService.getServiceRequestDetail(Number(id));
      const requestData = response.service_request || response;
      setRequest(requestData);

      // Check if already rated
      if (requestData.client_rating) {
        Alert.alert(
          'Already Rated',
          'You have already rated this service.',
          [{ text: 'OK', onPress: () => router.back() }]
        );
      }

      // Verify it's completed
      if (requestData.status !== 'completed') {
        Alert.alert(
          'Cannot Rate',
          'You can only rate completed services.',
          [{ text: 'OK', onPress: () => router.back() }]
        );
      }

      // Verify worker is assigned
      if (!requestData.assigned_worker) {
        Alert.alert(
          'No Worker Assigned',
          'Cannot rate: No worker was assigned to this service.',
          [{ text: 'OK', onPress: () => router.back() }]
        );
      }
    } catch (error: any) {
      console.error('Error loading request:', error);
      Alert.alert(t('common.error'), 'Failed to load service details');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (rating === 0) {
      Alert.alert('Rating Required', 'Please select a star rating before submitting.');
      return;
    }

    try {
      setSubmitting(true);
      await apiService.rateServiceRequest(Number(id), {
        rating,
        review: review.trim(),
      });

      Alert.alert(
        'Rating Submitted',
        'Thank you for your feedback!',
        [
          {
            text: 'OK',
            onPress: () => {
              router.back();
              // Optionally navigate to request detail to see the rating
              router.push(`/(client)/service-request/${id}` as any);
            },
          },
        ]
      );
    } catch (error: any) {
      console.error('Error submitting rating:', error);
      Alert.alert(
        'Error',
        error.response?.data?.error || 'Failed to submit rating. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Rate Worker" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>{t('requestService.loading')}</Text>
        </View>
      </View>
    );
  }

  if (!request) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Rate Worker" showBack />
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={64} color={theme.error} />
          <Text style={[styles.errorText, { color: theme.text }]}>
            Service not found
          </Text>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <Header title="Rate Worker" showBack />

      <ScrollView 
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Worker Info Card */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.workerHeader}>
            <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
              <Text style={styles.avatarText}>
                {request.assigned_worker?.full_name?.charAt(0) || 'W'}
              </Text>
            </View>
            <View style={styles.workerInfo}>
              <Text style={[styles.workerName, { color: theme.text }]}>
                {request.assigned_worker?.full_name || 'Worker'}
              </Text>
              <Text style={[styles.serviceName, { color: theme.textSecondary }]}>
                {request.title}
              </Text>
            </View>
          </View>
        </View>

        {/* Rating Section */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            How would you rate this service?
          </Text>
          <Text style={[styles.sectionDescription, { color: theme.textSecondary }]}>
            Your feedback helps us maintain quality standards
          </Text>

          <View style={styles.ratingContainer}>
            <StarRating
              rating={rating}
              onRatingChange={setRating}
              size={40}
              showLabel={true}
            />
          </View>
        </View>

        {/* Review Section */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Share your experience (Optional)
          </Text>
          <Text style={[styles.sectionDescription, { color: theme.textSecondary }]}>
            Tell us what went well or what could be improved
          </Text>

          <TextInput
            style={[
              styles.reviewInput,
              {
                backgroundColor: theme.background,
                color: theme.text,
                borderColor: theme.border,
              },
            ]}
            placeholder="Write your review here..."
            placeholderTextColor={theme.textTertiary}
            value={review}
            onChangeText={setReview}
            multiline
            numberOfLines={6}
            textAlignVertical="top"
            maxLength={500}
          />
          <Text style={[styles.characterCount, { color: theme.textTertiary }]}>
            {review.length}/500 characters
          </Text>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            { backgroundColor: rating > 0 ? theme.primary : theme.border },
          ]}
          onPress={handleSubmit}
          disabled={submitting || rating === 0}
          activeOpacity={0.8}
        >
          {submitting ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="checkmark-circle-outline" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>{t('common.submit')}</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Cancel Button */}
        <TouchableOpacity
          style={[styles.cancelButton, { borderColor: theme.border }]}
          onPress={() => router.back()}
          disabled={submitting}
        >
          <Text style={[styles.cancelButtonText, { color: theme.text }]}>{t('common.cancel')}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
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
  workerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: '700',
  },
  workerInfo: {
    flex: 1,
  },
  workerName: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 4,
  },
  serviceName: {
    fontSize: 14,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  sectionDescription: {
    fontSize: 14,
    marginBottom: 20,
  },
  ratingContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  reviewInput: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    minHeight: 120,
    marginBottom: 8,
  },
  characterCount: {
    fontSize: 12,
    textAlign: 'right',
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  cancelButton: {
    borderWidth: 1,
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});
