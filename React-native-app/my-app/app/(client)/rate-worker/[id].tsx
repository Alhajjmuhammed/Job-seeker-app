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
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import apiService from '../../../services/api';
import { useTranslation } from 'react-i18next';

export default function RateWorkerScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { theme, isDark } = useTheme();

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [workerName, setWorkerName] = useState('');
  const [rating, setRating] = useState(0);
  const [review, setReview] = useState('');

  useEffect(() => {
    // Load request detail to get worker name
    const loadRequest = async () => {
      try {
        setLoading(true);
        const response = await apiService.getServiceRequestDetail(Number(id));
        const requestData = response.service_request || response;
        // Get first accepted assignment's worker name if available
        const assignment = requestData.assignments?.[0];
        if (assignment?.worker?.full_name) {
          setWorkerName(assignment.worker.full_name);
        }
      } catch {
        // non-critical, just show generic text
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadRequest();
    }
  }, [id]);

  const handleSubmit = async () => {
    if (rating === 0) {
      Alert.alert(t('common.error'), t('rating.selectRating') || 'Please select a rating');
      return;
    }

    setSubmitting(true);
    try {
      await apiService.rateServiceRequest(Number(id), {
        rating,
        review: review.trim() || undefined,
      });
      Alert.alert(
        t('rating.thankYou') || 'Thank You!',
        t('rating.submitted') || 'Your rating has been submitted successfully.',
        [{ text: t('common.ok') || 'OK', onPress: () => router.back() }]
      );
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        // Backend (clients/api_views.py::rate_service_request) returns
        // validation failures as {'error': ...} (e.g. "You have already
        // rated this service request"), not 'message'/'detail' - those
        // keys never matched, so specific errors always fell through to
        // the generic fallback below.
        error.response?.data?.error ||
          error.response?.data?.message ||
          error.response?.data?.detail ||
          t('rating.submitFailed') ||
          'Failed to submit rating. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flexGrow: 1, padding: 24 },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingTop: Platform.OS === 'ios' ? 50 : 40,
      paddingHorizontal: 16,
      paddingBottom: 12,
      backgroundColor: theme.surface,
      borderBottomWidth: 1,
      borderBottomColor: theme.border,
    },
    backBtn: { padding: 4, marginRight: 12 },
    headerTitle: { fontSize: 18, fontFamily: theme.fontBold, color: theme.text },
    card: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 24,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.08,
      shadowRadius: 8,
      elevation: 3,
    },
    iconWrap: {
      alignSelf: 'center',
      width: 72,
      height: 72,
      borderRadius: 36,
      backgroundColor: theme.primary + '20',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 16,
    },
    workerLabel: {
      fontSize: 13,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
      textAlign: 'center',
      marginBottom: 4,
    },
    workerName: {
      fontSize: 18,
      fontFamily: theme.fontBold,
      color: theme.text,
      textAlign: 'center',
      marginBottom: 20,
    },
    sectionTitle: {
      fontSize: 15,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 12,
    },
    starsRow: {
      flexDirection: 'row',
      justifyContent: 'center',
      gap: 12,
      marginBottom: 8,
    },
    starBtn: { padding: 4 },
    ratingLabel: {
      fontSize: 13,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
      textAlign: 'center',
      marginBottom: 20,
    },
    reviewInput: {
      backgroundColor: theme.background,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: theme.border,
      padding: 14,
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.text,
      minHeight: 100,
      textAlignVertical: 'top',
    },
    submitBtn: {
      backgroundColor: theme.primary,
      borderRadius: 14,
      paddingVertical: 16,
      alignItems: 'center',
      marginTop: 8,
    },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: {
      fontSize: 16,
      fontFamily: theme.fontBold,
      color: '#FFFFFF',
    },
    skipBtn: {
      paddingVertical: 14,
      alignItems: 'center',
      marginTop: 8,
    },
    skipBtnText: {
      fontSize: 14,
      fontFamily: theme.fontRegular,
      color: theme.textSecondary,
    },
    loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  });

  const RATING_LABELS: Record<number, string> = {
    1: t('rating.terrible') || 'Terrible',
    2: t('rating.poor') || 'Poor',
    3: t('rating.okay') || 'Okay',
    4: t('rating.good') || 'Good',
    5: t('rating.excellent') || 'Excellent',
  };

  if (loading) {
    return (
      <View style={[s.container, s.loadingContainer]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style={isDark ? 'light' : 'dark'} />

      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={s.headerTitle}>{t('rating.rateWorker') || 'Rate Worker'}</Text>
      </View>

      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        <View style={s.card}>
          {/* Worker Icon */}
          <View style={s.iconWrap}>
            <Ionicons name="person" size={36} color={theme.primary} />
          </View>

          {/* Worker Name */}
          <Text style={s.workerLabel}>{t('rating.howWasYourExperience') || 'How was your experience with'}</Text>
          <Text style={s.workerName}>{workerName || t('rating.yourWorker') || 'Your Worker'}</Text>

          {/* Star Rating */}
          <Text style={s.sectionTitle}>{t('rating.selectRating') || 'Select a rating'}</Text>
          <View style={s.starsRow}>
            {[1, 2, 3, 4, 5].map((star) => (
              <TouchableOpacity key={star} style={s.starBtn} onPress={() => setRating(star)}>
                <Ionicons
                  name={star <= rating ? 'star' : 'star-outline'}
                  size={40}
                  color={star <= rating ? '#F59E0B' : theme.border}
                />
              </TouchableOpacity>
            ))}
          </View>
          {rating > 0 && (
            <Text style={s.ratingLabel}>{RATING_LABELS[rating]}</Text>
          )}

          {/* Review */}
          <Text style={s.sectionTitle}>{t('rating.leaveReview') || 'Leave a review (optional)'}</Text>
          <TextInput
            style={s.reviewInput}
            placeholder={t('rating.reviewPlaceholder') || 'Share details about your experience...'}
            placeholderTextColor={theme.textTertiary}
            multiline
            maxLength={500}
            value={review}
            onChangeText={setReview}
          />
        </View>

        {/* Submit */}
        <TouchableOpacity
          style={[s.submitBtn, (submitting || rating === 0) && s.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={submitting || rating === 0}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={s.submitBtnText}>{t('rating.submit') || 'Submit Rating'}</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={s.skipBtn} onPress={() => router.back()}>
          <Text style={s.skipBtnText}>{t('rating.skipForNow') || 'Skip for now'}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
