import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import { useTheme } from '../../../../../contexts/ThemeContext';
import Header from '../../../../../components/Header';
import apiService from '../../../../../services/api';

interface Assignment {
  id: number;
  assignment_number: number;
  status?: string;
  worker_accepted?: boolean;
  service_request: number; // Just the ID
  // Flattened service request fields from serializer
  title: string;
  category_name: string;
  location: string;
  city: string;
  client_name: string;
}

export default function ClockInScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [currentLocation, setCurrentLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  
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
      
      // Check if worker is already clocked in
      if (isClockedIn) {
        console.log('⚠️ Worker is already clocked in - redirecting back');
        Alert.alert(
          'Already Clocked In',
          'You are already clocked in. Please clock out first before clocking in again.',
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
      
      console.log('📋 Clock In Screen Loaded:', {
        assignmentId: assignmentData.id,
        status: assignmentData.status,
        workerAccepted: assignmentData.worker_accepted,
        isClockedIn: isClockedIn
      });
    } catch (error: any) {
      console.error('❌ Error loading assignment:', error);
      Alert.alert('Error', 'Failed to load assignment');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const requestLocationPermission = async () => {
    try {
      setLocationLoading(true);
      setLocationError(null);
      
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        setLocationError('Location permission denied. You can still clock in without location.');
        setLocationLoading(false);
        return;
      }

      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      setCurrentLocation({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });
      setLocationLoading(false);
    } catch (error) {
      console.error('Error getting location:', error);
      setLocationError('Could not get location. You can still clock in without it.');
      setLocationLoading(false);
    }
  };

  const handleClockIn = async () => {
    if (!assignment) return;

    // Check if assignment has been accepted
    if (assignment.worker_accepted !== true) {
      Alert.alert(
        'Assignment Not Accepted',
        'You must accept this assignment before you can clock in.'
      );
      return;
    }

    Alert.alert(
      'Confirm Clock In',
      'Are you ready to start working on this assignment?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Yes, Clock In',
          onPress: confirmClockIn,
        },
      ]
    );
  };

  const confirmClockIn = async () => {
    if (!assignment) return;
    
    // 🛡️ PREVENT CONCURRENT EXECUTION - Guard against double-tap
    if (isProcessingRef.current) {
      console.log('⚠️ Already processing clock in - ignoring duplicate request');
      return;
    }
    
    isProcessingRef.current = true;

    try {
      setSubmitting(true);
      
      // ✅ DOUBLE CHECK: Verify clock status RIGHT BEFORE API call
      console.log('🔍 Double-checking clock status before clock in...');
      const checkResponse = await apiService.getWorkerAssignmentDetail(assignment.id);
      const isAlreadyClockedIn = checkResponse.is_clocked_in === true;
      
      if (isAlreadyClockedIn) {
        console.log('⚠️ Clock status changed! Worker is ALREADY clocked in');
        Alert.alert(
          'Already Clocked In',
          'You have already clocked in. This may have happened from another action or if you clicked too quickly.',
          [
            {
              text: 'OK',
              onPress: () => {
                // Go back to assignment detail which will show correct state
                router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
              }
            }
          ]
        );
        return;
      }
      
      const result = await apiService.clockIn(assignment.id, currentLocation || undefined);
      console.log('✅ Clock In Success:', result);

      // Redirect immediately, show success after
      router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
      setTimeout(() => {
        Alert.alert('⏰ Clocked In Successfully!', 'Your work session has started. Time tracking is now active.');
      }, 100);
    } catch (error: any) {
      const isAlreadyClockedIn = error.response?.data?.error?.toLowerCase().includes('already clocked in');

      if (isAlreadyClockedIn) {
        // Worker is already clocked in — redirect silently, no error shown
        console.log('ℹ️ Clock in: already clocked in, redirecting');
        router.replace(`/(worker)/service-assignment/${assignment.id}` as any);
      } else {
        // Genuine error — show it
        console.error('❌ Clock In Error:', error.response?.data || error.message);
        const errorMessage = error.response?.data?.error || error.message || 'Failed to clock in. Please try again.';
        Alert.alert('Clock In Failed', errorMessage);
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

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Clock In" showBack />
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
        <Header title="Clock In" showBack />
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
      <Header title="Clock In" showBack />

      <ScrollView style={styles.content}>
        {/* Clock In Banner */}
        <View style={[styles.banner, { backgroundColor: theme.primary }]}>
          <Ionicons name="time-outline" size={48} color="#FFFFFF" />
          <Text style={styles.bannerTime}>{getCurrentTime()}</Text>
          <Text style={styles.bannerText}>Ready to Start Work?</Text>
        </View>

        {/* Assignment Info */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Assignment Details
          </Text>
          
          <Text style={[styles.assignmentTitle, { color: theme.text }]}>
            {assignment.title}
          </Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {assignment.category_name}
          </Text>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <Ionicons name="location-outline" size={20} color={theme.textSecondary} />
            <View style={styles.infoContent}>
              <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>
                Location
              </Text>
              <Text style={[styles.infoValue, { color: theme.text }]}>
                {assignment.location}, {assignment.city}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="person-outline" size={20} color={theme.textSecondary} />
            <View style={styles.infoContent}>
              <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>
                Client
              </Text>
              <Text style={[styles.infoValue, { color: theme.text }]}>
                {assignment.client_name}
              </Text>
            </View>
          </View>
        </View>

        {/* Location Status */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.locationHeader}>
            <Ionicons 
              name="location" 
              size={24} 
              color={currentLocation ? '#4CAF50' : '#FFA500'} 
            />
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Location Tracking
            </Text>
          </View>

          {locationLoading ? (
            <View style={styles.locationStatus}>
              <ActivityIndicator size="small" color={theme.primary} />
              <Text style={[styles.locationText, { color: theme.textSecondary }]}>
                Getting your location...
              </Text>
            </View>
          ) : currentLocation ? (
            <View style={[styles.locationSuccess, { backgroundColor: '#4CAF50' + '20' }]}>
              <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
              <Text style={[styles.locationSuccessText, { color: '#4CAF50' }]}>
                Location captured successfully
              </Text>
            </View>
          ) : (
            <View style={[styles.locationWarning, { backgroundColor: '#FFA500' + '20' }]}>
              <Ionicons name="warning-outline" size={20} color="#FFA500" />
              <Text style={[styles.locationWarningText, { color: '#FFA500' }]}>
                {locationError || 'Location not available'}
              </Text>
              <TouchableOpacity
                style={[styles.retryButton, { backgroundColor: theme.primary }]}
                onPress={requestLocationPermission}
              >
                <Text style={styles.retryButtonText}>Retry</Text>
              </TouchableOpacity>
            </View>
          )}

          <Text style={[styles.locationNote, { color: theme.textSecondary }]}>
            📍 Location helps verify your attendance and improves service quality
          </Text>
        </View>

        {/* Important Notes */}
        <View style={[styles.infoBox, { backgroundColor: '#E3F2FD' }]}>
          <Ionicons name="information-circle" size={24} color="#2196F3" />
          <View style={styles.infoBoxContent}>
            <Text style={styles.infoBoxTitle}>Important</Text>
            <Text style={styles.infoBoxText}>
              • Remember to clock out when you finish
            </Text>
            <Text style={styles.infoBoxText}>
              • Time tracking starts immediately after clock in
            </Text>
            <Text style={styles.infoBoxText}>
              • You can take breaks by clocking out and back in
            </Text>
          </View>
        </View>

        {/* Clock In Button */}
        <View style={styles.actionContainer}>
          <TouchableOpacity
            style={[styles.clockInButton, { backgroundColor: theme.primary }]}
            onPress={handleClockIn}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="play-circle" size={28} color="#FFFFFF" />
                <Text style={styles.clockInButtonText}>Clock In Now</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.cancelButton, { borderColor: theme.border }]}
            onPress={() => router.back()}
          >
            <Text style={[styles.cancelButtonText, { color: theme.text }]}>
              Cancel
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
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  assignmentTitle: {
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
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 12,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  locationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  locationStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    gap: 8,
  },
  locationText: {
    fontSize: 14,
  },
  locationSuccess: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    gap: 8,
    marginBottom: 12,
  },
  locationSuccessText: {
    fontSize: 14,
    fontWeight: '600',
  },
  locationWarning: {
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  locationWarningText: {
    fontSize: 14,
    marginBottom: 8,
  },
  retryButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    marginTop: 4,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
  locationNote: {
    fontSize: 12,
    fontStyle: 'italic',
  },
  infoBox: {
    flexDirection: 'row',
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  infoBoxContent: {
    flex: 1,
  },
  infoBoxTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2196F3',
    marginBottom: 8,
  },
  infoBoxText: {
    fontSize: 12,
    color: '#1976D2',
    marginBottom: 4,
  },
  actionContainer: {
    padding: 16,
  },
  clockInButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 18,
    borderRadius: 12,
    marginBottom: 12,
    gap: 10,
  },
  clockInButtonText: {
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
