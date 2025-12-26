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
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import apiService from '../../../services/api';

interface WorkerInfo {
  id: number;
  name: string;
  category: string;
  hourlyRate: number;
  rating: number;
}

export default function RequestWorkerScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [worker, setWorker] = useState<WorkerInfo | null>(null);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    budget: '',
    location: '',
    startDate: '',
  });

  useEffect(() => {
    loadWorkerInfo();
  }, [id]);

  const loadWorkerInfo = async () => {
    try {
      setLoading(true);
      const workerData = await apiService.getWorkerDetail(Number(id));
      setWorker({
        id: workerData.id,
        name: workerData.name,
        category: workerData.categories?.[0]?.name || 'General',
        hourlyRate: parseFloat(workerData.hourly_rate || '0'),
        rating: workerData.average_rating || 0,
      });
    } catch (error) {
      console.error('Error loading worker:', error);
      Alert.alert('Error', 'Failed to load worker details');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    // Validate form
    if (!formData.title.trim()) {
      Alert.alert('Error', 'Please enter a job title');
      return;
    }
    if (!formData.description.trim()) {
      Alert.alert('Error', 'Please enter a job description');
      return;
    }
    if (!formData.budget.trim()) {
      Alert.alert('Error', 'Please enter a budget');
      return;
    }
    if (!formData.location.trim()) {
      Alert.alert('Error', 'Please enter a location');
      return;
    }

    try {
      setSubmitting(true);
      await apiService.createJobRequest({
        ...formData,
        worker_id: Number(id),
        category: worker?.category || 'General',
      });
      
      Alert.alert(
        'Success',
        'Job request sent successfully!',
        [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
    } catch (error) {
      console.error('Error creating job request:', error);
      Alert.alert('Error', 'Failed to send job request. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={theme.textLight} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Request Worker</Text>
          <View style={styles.headerRight} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>Loading...</Text>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.primary }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.textLight} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>Request Worker</Text>
        <View style={styles.headerRight} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Worker Info Card */}
        <View style={[styles.workerCard, { backgroundColor: theme.card }]}>
          <View style={[styles.workerAvatar, { backgroundColor: theme.primary }]}>
            <Text style={[styles.workerAvatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
              {worker?.name[0]}
            </Text>
          </View>
          <View style={styles.workerInfo}>
            <Text style={[styles.workerName, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
              {worker?.name}
            </Text>
            <Text style={[styles.workerCategory, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              {worker?.category}
            </Text>
            <View style={styles.workerDetails}>
              <View style={styles.detailItem}>
                <Ionicons name="star" size={16} color="#FCD34D" />
                <Text style={[styles.detailText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  {worker?.rating.toFixed(1)}
                </Text>
              </View>
              <View style={styles.detailItem}>
                <Ionicons name="cash" size={16} color={theme.primary} />
                <Text style={[styles.detailText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
                  SDG {worker?.hourlyRate}/hr
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* Form */}
        <View style={[styles.formCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.formTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>Job Details</Text>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>Job Title *</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
              placeholder="e.g., Fix leaking pipe"
              placeholderTextColor={theme.textSecondary}
              value={formData.title}
              onChangeText={(text) => setFormData({ ...formData, title: text })}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>Description *</Text>
            <TextInput
              style={[styles.textArea, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
              placeholder="Describe the job in detail..."
              placeholderTextColor={theme.textSecondary}
              value={formData.description}
              onChangeText={(text) => setFormData({ ...formData, description: text })}
              multiline
              numberOfLines={6}
              textAlignVertical="top"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>Budget (SDG) *</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
              placeholder="e.g., 500"
              placeholderTextColor={theme.textSecondary}
              value={formData.budget}
              onChangeText={(text) => setFormData({ ...formData, budget: text })}
              keyboardType="numeric"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>Location *</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
              placeholder="e.g., Khartoum, Sudan"
              placeholderTextColor={theme.textSecondary}
              value={formData.location}
              onChangeText={(text) => setFormData({ ...formData, location: text })}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>Preferred Start Date</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
              placeholder="e.g., Tomorrow, Next week"
              placeholderTextColor={theme.textSecondary}
              value={formData.startDate}
              onChangeText={(text) => setFormData({ ...formData, startDate: text })}
            />
          </View>
        </View>

        {/* Info Card */}
        <View style={[styles.infoCard, { backgroundColor: '#DBEAFE' }]}>
          <Ionicons name="information-circle" size={24} color="#1E40AF" />
          <Text style={[styles.infoText, { fontFamily: 'Poppins_400Regular' }]}>
            The worker will receive your request and can accept or decline it. You'll be notified of their response.
          </Text>
        </View>
      </ScrollView>

      {/* Submit Button */}
      <View style={[styles.bottomSection, { backgroundColor: theme.card, borderTopColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.submitButton, { backgroundColor: theme.primary, opacity: submitting ? 0.6 : 1 }]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color={theme.textLight} />
          ) : (
            <>
              <Ionicons name="send" size={20} color={theme.textLight} />
              <Text style={[styles.submitButtonText, { color: theme.textLight, fontFamily: 'Poppins_600SemiBold' }]}>
                Send Request
              </Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  workerCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    flexDirection: 'row',
    gap: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  workerAvatar: {
    width: 70,
    height: 70,
    borderRadius: 35,
    justifyContent: 'center',
    alignItems: 'center',
  },
  workerAvatarText: {
    fontSize: 28,
  },
  workerInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  workerName: {
    fontSize: 18,
    marginBottom: 4,
  },
  workerCategory: {
    fontSize: 14,
    marginBottom: 8,
  },
  workerDetails: {
    flexDirection: 'row',
    gap: 16,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  detailText: {
    fontSize: 14,
  },
  formCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  formTitle: {
    fontSize: 20,
    marginBottom: 20,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 15,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    minHeight: 120,
  },
  infoCard: {
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
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
