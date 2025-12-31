import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import { useRatingRefresh } from '../../../contexts/RatingContext';
import apiService from '../../../services/api';

export default function RateWorkerScreen() {
  const { workerId, workerName } = useLocalSearchParams();
  const { theme } = useTheme();
  const { triggerRatingRefresh, refreshTrigger } = useRatingRefresh();
  const [rating, setRating] = useState(0);
  const [review, setReview] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentRating, setCurrentRating] = useState<number>(0);

  useEffect(() => {
    if (!workerId) {
      console.log('No workerId available yet, skipping load');
      return;
    }
    console.log('Initial load triggered for workerId:', workerId);
    loadWorkerData();
  }, [workerId]);

  // Also load when screen comes into focus (handles app reload scenarios)
  useFocusEffect(
    React.useCallback(() => {
      if (!workerId) {
        console.log('Focus effect: No workerId available yet');
        return;
      }
      console.log('Focus effect triggered, loading worker data');
      loadWorkerData();
    }, [workerId])
  );

  // Also refresh when global rating trigger changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      console.log('Refreshing due to rating trigger:', refreshTrigger);
      loadWorkerData();
    }
  }, [refreshTrigger]);

  const loadWorkerData = async () => {
    try {
      console.log('=== Starting loadWorkerData for workerId:', workerId);
      setLoading(true);
      
      if (!workerId) {
        console.log('No workerId provided, skipping load');
        setCurrentRating(0);
        return;
      }
      
      const workerData = await apiService.getWorkerDetail(Number(workerId));
      console.log('API Response:', JSON.stringify(workerData, null, 2));
      
      const rawRating = workerData.average_rating;
      console.log('Raw rating from API:', rawRating, 'Type:', typeof rawRating);
      
      let rating = 0;
      if (rawRating !== null && rawRating !== undefined && rawRating !== '') {
        rating = Number(rawRating);
        if (isNaN(rating)) {
          console.warn('Rating is NaN, setting to 0');
          rating = 0;
        }
      }
      
      console.log('Final parsed rating:', rating);
      setCurrentRating(rating);
      // Pre-fill the rating input with current rating
      setRating(Math.round(rating));
      console.log('State updated with rating:', rating, 'Input pre-filled with:', Math.round(rating));
      
    } catch (error) {
      console.error('Error loading worker data:', error);
      setCurrentRating(0);
      setRating(0);
    } finally {
      setLoading(false);
      console.log('=== Finished loadWorkerData, loading set to false');
    }
  };

  const handleStarPress = (starRating: number) => {
    setRating(starRating);
  };

  const handleSubmit = async () => {
    if (rating === 0) {
      Alert.alert('Error', 'Please select a rating');
      return;
    }

    try {
      setSubmitting(true);
      
      // Optimistic update - immediately show the new rating
      setCurrentRating(rating);
      
      await apiService.rateWorker(Number(workerId), {
        rating,
        review: review.trim(),
      });
      
      // Give backend a moment to calculate the new average rating
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Reload worker data to get the actual calculated average
      await loadWorkerData();
      
      // Trigger global rating refresh across all screens
      triggerRatingRefresh();
      
      Alert.alert(
        'Success',
        'Thank you for your feedback! Updated rating is now displayed.',
        [
          {
            text: 'OK',
            onPress: () => {
              // Go back to worker profile - it will automatically refresh
              router.back();
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error submitting rating:', error);
      Alert.alert('Error', 'Failed to submit rating. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const getRatingText = () => {
    switch (rating) {
      case 1: return 'Poor';
      case 2: return 'Fair';
      case 3: return 'Good';
      case 4: return 'Very Good';
      case 5: return 'Excellent';
      default: return 'Tap stars to rate';
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.primary }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.textLight} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>
          Rate Worker
        </Text>
        <View style={styles.headerRight} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              Loading worker data...
            </Text>
          </View>
        ) : (
          <>
            {/* Worker Info */}
            <View style={[styles.workerCard, { backgroundColor: theme.card }]}>
              <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
                <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
                  {(workerName as string)?.[0] || 'W'}
                </Text>
              </View>
              <View style={styles.workerInfo}>
                <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                  {workerName}
                </Text>
                <Text style={[styles.workerSubtitle, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  How was your experience?
                </Text>
              </View>
            </View>

            {/* Current Rating Display - Always show this section */}
            <View style={[styles.currentRatingCard, { backgroundColor: theme.card }]}>
              <Text style={[styles.currentRatingTitle, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                Current Rating
              </Text>
              <View style={styles.currentRatingDisplay}>
                <Ionicons name="star" size={20} color="#F59E0B" />
                <Text style={[styles.currentRatingText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>
                  {loading ? 'Loading...' : (currentRating > 0) ? currentRating.toFixed(1) : 'No ratings yet'}
                </Text>
              </View>
            </View>

                {/* Rating Stars */}
            <View style={[styles.ratingCard, { backgroundColor: theme.card }]}>
              <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                Rate this worker
              </Text>
              
              <View style={styles.starsContainer}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <TouchableOpacity
                    key={star}
                    onPress={() => handleStarPress(star)}
                    style={[
                      styles.starButton,
                      star <= rating && { backgroundColor: '#FFF3CD', borderColor: '#FCD34D' }
                    ]}
                    activeOpacity={0.7}
                  >
                    <Ionicons
                      name={star <= rating ? 'star' : 'star-outline'}
                      size={32}
                      color={star <= rating ? '#F59E0B' : theme.textSecondary}
                    />
                  </TouchableOpacity>
                ))}
              </View>
              
              <Text style={[styles.ratingText, { color: theme.primary, fontFamily: 'Poppins_600SemiBold' }]}>
                {getRatingText()}
              </Text>
            </View>

            {/* Review */}
            <View style={[styles.card, { backgroundColor: theme.card }]}>
              <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
                Write a review (optional)
              </Text>
              <TextInput
                style={[styles.textArea, { 
                  backgroundColor: theme.background, 
                  color: theme.text, 
                  borderColor: theme.border,
                  fontFamily: 'Poppins_400Regular' 
                }]}
                placeholder="Tell others about your experience with this worker..."
                placeholderTextColor={theme.textSecondary}
                value={review}
                onChangeText={setReview}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
                maxLength={500}
              />
              <Text style={[styles.charCount, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                {review.length}/500 characters
              </Text>
            </View>
          </>
        )}
      </ScrollView>

      {/* Submit Button */}
      <View style={[styles.bottomSection, { backgroundColor: theme.card, borderTopColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.submitButton, { 
            backgroundColor: rating > 0 ? theme.primary : theme.textSecondary,
            opacity: submitting ? 0.7 : 1 
          }]}
          onPress={handleSubmit}
          disabled={rating === 0 || submitting}
          activeOpacity={0.8}
        >
          {submitting ? (
            <ActivityIndicator color={theme.textLight} size="small" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={20} color={theme.textLight} />
              <Text style={[styles.submitButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>
                Submit Rating
              </Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  headerTitle: {
    fontSize: 20,
  },
  headerRight: {
    width: 40,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  workerCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  workerAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  workerAvatarText: {
    fontSize: 24,
  },
  workerInfo: {
    flex: 1,
  },
  workerName: {
    fontSize: 20,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
  },
  ratingCard: {
    borderRadius: 16,
    padding: 24,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    alignItems: 'center',
  },
  card: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    marginBottom: 20,
    textAlign: 'center',
  },
  starsContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 16,
    gap: 8,
  },
  starButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  ratingText: {
    fontSize: 18,
    textAlign: 'center',
    marginTop: 8,
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    fontSize: 15,
    minHeight: 100,
    marginBottom: 8,
  },
  charCount: {
    fontSize: 12,
    textAlign: 'right',
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 14,
  },
  currentRatingCard: {
    padding: 16,
    borderRadius: 16,
    marginBottom: 20,
    alignItems: 'center',
  },
  currentRatingTitle: {
    fontSize: 14,
    marginBottom: 8,
  },
  currentRatingDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  currentRatingText: {
    fontSize: 18,
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    borderTopWidth: 1,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 12,
    padding: 16,
  },
  submitButtonText: {
    fontSize: 16,
  },
});