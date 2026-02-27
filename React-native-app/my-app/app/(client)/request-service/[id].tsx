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
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';

interface ServiceCategory {
  id: number;
  name: string;
  description: string;
  icon: string;
}

export default function RequestServiceScreen() {
  const { id: categoryId } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [category, setCategory] = useState<ServiceCategory | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    location: '',
    city: '',
    estimated_duration_hours: '1',
    urgency: 'normal',
    client_notes: '',
  });

  useEffect(() => {
    loadCategoryDetails();
  }, [categoryId]);

  const loadCategoryDetails = async () => {
    try {
      setLoading(true);
      const response = await apiService.getServices();
      const foundCategory = response.services.find((s: any) => s.id === parseInt(categoryId as string));
      setCategory(foundCategory);
      if (foundCategory) {
        setFormData(prev => ({
          ...prev,
          title: `${foundCategory.name} Service Request`
        }));
      }
    } catch (error) {
      console.error('Error loading category:', error);
      Alert.alert('Error', 'Failed to load service details');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    if (!formData.description.trim()) {
      Alert.alert('Validation Error', 'Please provide a detailed description of your service needs');
      return false;
    }
    if (!formData.location.trim()) {
      Alert.alert('Validation Error', 'Please specify the location for the service');
      return false;
    }
    if (!formData.city.trim()) {
      Alert.alert('Validation Error', 'Please specify the city');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    try {
      setSubmitting(true);
      const submitData = {
        title: formData.title,
        description: formData.description,
        location: formData.location,
        city: formData.city,
        estimated_duration_hours: parseFloat(formData.estimated_duration_hours),
        urgency: formData.urgency,
        client_notes: formData.client_notes || undefined,
      };

      const response = await apiService.requestService(parseInt(categoryId as string), submitData);
      
      Alert.alert(
        'Request Submitted!',
        'Your service request has been submitted successfully. Our admin will assign a qualified worker soon.',
        [
          {
            text: 'View My Requests',
            onPress: () => router.replace('/(client)/my-requests'),
          },
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
    } catch (error: any) {
      console.error('Error submitting request:', error);
      Alert.alert(
        'Submission Failed',
        error.response?.data?.error || 'Failed to submit service request. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Request Service" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>Loading service details...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title={`Request ${category?.name || 'Service'}`} showBack />
      
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {category && (
          <View style={[styles.serviceCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.serviceName, { color: theme.text }]}>
              {category.name}
            </Text>
            <Text style={[styles.serviceDescription, { color: theme.textSecondary }]}>
              {category.description}
            </Text>
          </View>
        )}

        <Text style={[styles.infoText, { color: theme.textSecondary }]}>
          Fill out the details below and our team will assign the most suitable worker for your needs.
        </Text>

        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Service Title</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.title}
              onChangeText={(value) => handleInputChange('title', value)}
              placeholder="Brief title for your service request"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>
              Description <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.textArea, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.description}
              onChangeText={(value) => handleInputChange('description', value)}
              placeholder="Provide detailed description of what you need..."
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={4}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>
              Location <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.location}
              onChangeText={(value) => handleInputChange('location', value)}
              placeholder="Full address or area where service is needed"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>
              City <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.city}
              onChangeText={(value) => handleInputChange('city', value)}
              placeholder="City name"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Estimated Duration (Hours)</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.estimated_duration_hours}
              onChangeText={(value) => handleInputChange('estimated_duration_hours', value)}
              placeholder="1"
              placeholderTextColor={theme.textSecondary}
              keyboardType="numeric"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Urgency</Text>
            <View style={styles.urgencyButtons}>
              {['normal', 'urgent', 'emergency'].map((urgency) => (
                <TouchableOpacity
                  key={urgency}
                  style={[
                    styles.urgencyButton,
                    { borderColor: theme.border },
                    formData.urgency === urgency && { backgroundColor: theme.primary }
                  ]}
                  onPress={() => handleInputChange('urgency', urgency)}
                >
                  <Text
                    style={[
                      styles.urgencyText,
                      { color: formData.urgency === urgency ? '#FFFFFF' : theme.text }
                    ]}
                  >
                    {urgency.charAt(0).toUpperCase() + urgency.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Additional Notes (Optional)</Text>
            <TextInput
              style={[styles.input, styles.textArea, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={formData.client_notes}
              onChangeText={(value) => handleInputChange('client_notes', value)}
              placeholder="Any special requirements or additional information..."
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>
        </View>

        <TouchableOpacity
          style={[
            styles.submitButton,
            { backgroundColor: theme.primary },
            submitting && styles.submitButtonDisabled
          ]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="send" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>Submit Service Request</Text>
            </>
          )}
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={[styles.footerText, { color: theme.textSecondary }]}>
            After submission, our team will review your request and assign a qualified worker. 
            You'll be notified within 2-4 hours with the assigned worker's contact details.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    fontSize: 16,
  },
  serviceCard: {
    padding: 20,
    borderRadius: 12,
    marginBottom: 16,
  },
  serviceName: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  serviceDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  infoText: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 16,
  },
  form: {
    gap: 20,
  },
  inputGroup: {
    gap: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
  },
  required: {
    color: '#FF3B30',
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  flex1: {
    flex: 1,
  },
  marginRight: {
    marginRight: 6,
  },
  urgencyButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  urgencyButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderRadius: 8,
    alignItems: 'center',
  },
  urgencyText: {
    fontSize: 14,
    fontWeight: '500',
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 32,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  footer: {
    marginTop: 24,
    padding: 16,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
});