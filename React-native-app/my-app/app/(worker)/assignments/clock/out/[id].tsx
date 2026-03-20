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
import * as Location from 'expo-location';
import { useTheme } from '../../../../../contexts/ThemeContext';
import Header from '../../../../../components/Header';
import apiService from '../../../../../services/api';
import { useTranslation } from 'react-i18next';

interface Assignment {
  id: number;
  assignment_number: number;
  status: string;
  worker_accepted: boolean;
  service_request: number; // Just the ID
  // Flattened service request fields from serializer
  title: string;
  category_name: string;
  location: string;
  city: string;
  client_name: string;
}

export default function ClockOutScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [notes, setNotes] = useState('');
  const [currentLocation, setCurrentLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [workStartTime] = useState(new Date());
  
  // 🛡️ Prevent double-tap/concurrent execution
  const isProcessingRef = React.useRef(false);

  useEffect(() => {
    loadAssignment();
    requestLocationPermission();
  }, [id]);

  const loadAssignment = async () => {
    try {
      setLoading(true);
      const response = await apiService.getWorkerAssignmentDetail(Number(id));
      const assignmentData = response.assignment || response;
      const isClockedIn = response.is_clocked_in === true;
      
      // Check if worker is actually clocked in
      if (!isClockedIn) {
        console.log('⚠️ Worker is not clocked in - redirecting back');
        Alert.alert(
          'Not Clocked In',
          'You are not currently clocked in. Please clock in first before you can clock out.',
          [
            {
              text: 'OK',
              onPress: () => router.back()
            }
          ]
        );
        return;
      }
      
      setAssignment(assignmentData);
      
      console.log('📋 Clock Out Screen Loaded:', {
        assignmentId: assignmentData.id,
        status: assignmentData.status,
        workerAccepted: assignmentData.worker_accepted,
        serviceRequestTitle: assignmentData.title,
        isClockedIn: isClockedIn
      });
    } catch (error: any) {
      console.error('❌ Error loading assignment:', error);
      Alert.alert(t('common.error'), 'Failed to load assignment');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const requestLocationPermission = async () => {
    try {
      setLocationLoading(true);
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status === 'granted') {
        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        setCurrentLocation({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });
      }
    } catch (error) {
      console.error('❌ Error getting location:', error);
      setLocationError('Could not get location. You can still clock out without it.');
    } finally {
      setLocationLoading(false);
    }
  };

  const handleClockOut = async () => {
    if (!assignment) return;

    Alert.alert(
      'Confirm Clock Out',
      'Are you finished working for now? You can clock back in later if needed.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Yes, Clock Out',
          onPress: confirmClockOut,
        },
      ]
    );
  };

  const confirmClockOut = async () => {
    if (!assignment) return;

    // 🛡️ Prevent concurrent execution (double-tap guard)
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;

    try {
      setSubmitting(true);

      const result = await apiService.clockOut(
        assignment.id,
        currentLocation || undefined,
        notes.trim() || undefined
      );
      console.log('✅ Clock Out Success:', result);

      // Redirect immediately, show success after
      router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
      setTimeout(() => {
        Alert.alert('✅ Clocked Out Successfully!', 'Your work session has been recorded.');
      }, 100);
    } catch (error: any) {
      const isNotClockedIn = error.response?.data?.error?.toLowerCase().includes('not clocked in');

      if (isNotClockedIn) {
        // Worker is already clocked out — redirect silently, no error shown
        console.log('ℹ️ Clock out: already clocked out, redirecting');
        router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
      } else {
        // Genuine error — show it
        console.error('❌ Clock Out Error:', error.response?.data || error.message);
        const errorMessage = error.response?.data?.error || error.message || 'Failed to clock out. Please try again.';
        Alert.alert('Clock Out Failed', errorMessage);
      }
    } finally {
      setSubmitting(false);
      isProcessingRef.current = false;
    }
  };

  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const calculateWorkDuration = () => {
    const now = new Date();
    const diff = now.getTime() - workStartTime.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours === 0) return `${minutes} minutes`;
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Clock Out" showBack />
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
        <Header title="Clock Out" showBack />
        <View style={styles.errorContainer}>
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>{t('assignments.active')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Clock Out" showBack />

      <ScrollView style={styles.content}>
        {/* Clock Out Banner */}
        <View style={[styles.banner, { backgroundColor: '#F44336' }]}>
          <Ionicons name="stop-circle-outline" size={48} color="#FFFFFF" />
          <Text style={styles.bannerTime}>{getCurrentTime()}</Text>
          <Text style={styles.bannerText}>Ready to Clock Out?</Text>
        </View>

        {/* Work Duration */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.durationHeader}>
            <Ionicons name="time" size={32} color={theme.primary} />
            <View style={styles.durationInfo}>
              <Text style={[styles.durationLabel, { color: theme.textSecondary }]}>
                Work Duration
              </Text>
              <Text style={[styles.durationValue, { color: theme.text }]}>
                {calculateWorkDuration()}
              </Text>
            </View>
          </View>
        </View>

        {/* Assignment Info */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Assignment Summary
          </Text>
          
          <Text style={[styles.assignmentTitle, { color: theme.text }]}>
            {assignment.title}
          </Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {assignment.category_name}
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
              {assignment.client_name}
            </Text>
          </View>
        </View>

        {/* Location Status */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.locationHeader}>
            <Ionicons 
              name="location" 
              size={20} 
              color={currentLocation ? '#4CAF50' : '#FFA500'} 
            />
            <Text style={[styles.locationTitle, { color: theme.text }]}>
              Location Status
            </Text>
          </View>

          {locationLoading ? (
            <View style={styles.locationStatus}>
              <ActivityIndicator size="small" color={theme.primary} />
              <Text style={[styles.locationText, { color: theme.textSecondary }]}>
                Getting location...
              </Text>
            </View>
          ) : currentLocation ? (
            <View style={[styles.locationSuccess, { backgroundColor: '#4CAF50' + '20' }]}>
              <Ionicons name="checkmark-circle" size={18} color="#4CAF50" />
              <Text style={[styles.locationSuccessText, { color: '#4CAF50' }]}>
                Location captured
              </Text>
            </View>
          ) : (
            <View style={[styles.locationWarning, { backgroundColor: '#FFA500' + '20' }]}>
              <Ionicons name="warning-outline" size={18} color="#FFA500" />
              <Text style={[styles.locationWarningText, { color: '#FFA500' }]}>
                Location unavailable
              </Text>
            </View>
          )}
        </View>

        {/* Work Notes */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Work Notes (Optional)
          </Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
            Describe what you accomplished during this session
          </Text>

          <TextInput
            style={[
              styles.textArea,
              { backgroundColor: theme.background, color: theme.text },
            ]}
            placeholder={t('assignments.completed')}
            placeholderTextColor={theme.textSecondary}
            value={notes}
            onChangeText={setNotes}
            multiline
            numberOfLines={5}
          />
        </View>

        {/* Clock Out Button */}
        <View style={styles.actionContainer}>
          <TouchableOpacity
            style={[styles.clockOutButton, { backgroundColor: '#F44336' }]}
            onPress={handleClockOut}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="stop-circle" size={28} color="#FFFFFF" />
                <Text style={styles.clockOutButtonText}>Clock Out Now</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.cancelButton, { borderColor: theme.border }]}
            onPress={() => router.back()}
          >
            <Text style={[styles.cancelButtonText, { color: theme.text }]}>{t('worker.continue')}</Text>
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
  bannerTime: {
    color: '#FFFFFF',
    fontSize: 48,
    fontWeight: '700',
    marginTop: 16,
  },
  bannerText: {
    color: '#FFFFFF',
    fontSize: 18,
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
  durationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  durationInfo: {
    flex: 1,
  },
  durationLabel: {
    fontSize: 14,
    marginBottom: 4,
  },
  durationValue: {
    fontSize: 28,
    fontWeight: '700',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  assignmentTitle: {
    fontSize: 18,
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
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  infoText: {
    fontSize: 14,
  },
  locationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  locationTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  locationStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  locationText: {
    fontSize: 14,
  },
  locationSuccess: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    gap: 6,
  },
  locationSuccessText: {
    fontSize: 13,
    fontWeight: '600',
  },
  locationWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    gap: 6,
  },
  locationWarningText: {
    fontSize: 13,
  },
  subtitle: {
    fontSize: 14,
    marginBottom: 12,
  },
  textArea: {
    padding: 12,
    borderRadius: 8,
    fontSize: 14,
    minHeight: 120,
    textAlignVertical: 'top',
    marginBottom: 12,
  },
  actionContainer: {
    padding: 16,
  },
  clockOutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 18,
    borderRadius: 12,
    marginBottom: 12,
    gap: 10,
  },
  clockOutButtonText: {
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
