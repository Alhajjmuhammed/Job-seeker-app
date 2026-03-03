import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import DateTimePicker from '@react-native-community/datetimepicker';

interface ServiceRequestDetail {
  id: number;
  title: string;
  description: string;
  category: number;
  category_name: string;
  location: string;
  city: string;
  preferred_date?: string;
  preferred_time?: string;
  duration_type?: string;
  duration_days?: number;
  daily_rate?: number;
  total_price?: number;
  service_start_date?: string;
  service_end_date?: string;
  estimated_duration_hours: number;
  urgency: string;
  client_notes?: string;
  status: string;
}

interface PriceCalculation {
  duration_days: number;
  daily_rate: number;
  total_price: number;
  duration_type_display: string;
}

// Helper function to format dates
function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function EditServiceRequestScreen() {
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [request, setRequest] = useState<ServiceRequestDetail | null>(null);
  
  // Form state
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number>(0);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [city, setCity] = useState('');
  const [preferredDate, setPreferredDate] = useState<Date>(new Date());
  const [preferredTime, setPreferredTime] = useState<Date>(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  
  // Duration & Pricing state
  const [durationType, setDurationType] = useState<'daily' | 'monthly' | '3_months' | '6_months' | 'yearly' | 'custom'>('daily');
  const [serviceStartDate, setServiceStartDate] = useState<Date>(new Date());
  const [serviceEndDate, setServiceEndDate] = useState<Date>(new Date());
  const [showStartDatePicker, setShowStartDatePicker] = useState(false);
  const [showEndDatePicker, setShowEndDatePicker] = useState(false);
  const [priceCalculation, setPriceCalculation] = useState<PriceCalculation | null>(null);
  const [calculatingPrice, setCalculatingPrice] = useState(false);
  
  const [urgency, setUrgency] = useState<'normal' | 'urgent' | 'emergency'>('normal');
  const [clientNotes, setClientNotes] = useState('');

  useEffect(() => {
    loadRequestDetail();
  }, [id]);

  const loadRequestDetail = async () => {
    try {
      setLoading(true);
      const response = await apiService.getServiceRequestDetail(Number(id));
      const requestData = response.service_request || response;
      
      if (requestData.status !== 'pending') {
        Alert.alert(
          'Cannot Edit',
          'Only pending requests can be edited',
          [{ text: 'OK', onPress: () => router.back() }]
        );
        return;
      }

      setRequest(requestData);
      setSelectedCategory(requestData.category || 0);
      setTitle(requestData.title);
      setDescription(requestData.description);
      setLocation(requestData.location);
      setCity(requestData.city);
      setDurationType(requestData.duration_type || 'daily');
      setUrgency(requestData.urgency || 'normal');
      setClientNotes(requestData.client_notes || '');
      
      if (requestData.preferred_date) {
        setPreferredDate(new Date(requestData.preferred_date));
      }
      if (requestData.preferred_time) {
        const [hours, minutes] = requestData.preferred_time.split(':');
        const timeDate = new Date();
        timeDate.setHours(parseInt(hours), parseInt(minutes));
        setPreferredTime(timeDate);
      }
      
      // Load custom date range if exists
      if (requestData.duration_type === 'custom' && requestData.service_start_date && requestData.service_end_date) {
        setServiceStartDate(new Date(requestData.service_start_date));
        setServiceEndDate(new Date(requestData.service_end_date));
      }
    } catch (error: any) {
      console.error('Error loading request:', error);
      Alert.alert('Error', 'Failed to load request details');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const calculatePrice = useCallback(async () => {
    if (!selectedCategory) return;

    try {
      setCalculatingPrice(true);
      const data: any = {
        category_id: selectedCategory,
        duration_type: durationType,
      };

      if (durationType === 'custom') {
        data.start_date = serviceStartDate.toISOString().split('T')[0];
        data.end_date = serviceEndDate.toISOString().split('T')[0];
      }

      const response = await apiService.calculatePrice(data);
      setPriceCalculation(response);
    } catch (error: any) {
      console.error('Error calculating price:', error);
      setPriceCalculation(null);
    } finally {
      setCalculatingPrice(false);
    }
  }, [selectedCategory, durationType, serviceStartDate, serviceEndDate]);

  useEffect(() => {
    if (selectedCategory) {
      calculatePrice();
    }
  }, [selectedCategory, calculatePrice]);

  const validateForm = (): boolean => {
    if (!selectedCategory) {
      Alert.alert('Validation Error', 'Please select a service category');
      return false;
    }
    if (!title.trim()) {
      Alert.alert('Validation Error', 'Please enter a title');
      return false;
    }
    if (!description.trim()) {
      Alert.alert('Validation Error', 'Please enter a description');
      return false;
    }
    if (!location.trim()) {
      Alert.alert('Validation Error', 'Please enter a location');
      return false;
    }
    if (!city.trim()) {
      Alert.alert('Validation Error', 'Please enter a city');
      return false;
    }
    if (!priceCalculation) {
      Alert.alert('Error', 'Price calculation is required');
      return false;
    }
    if (durationType === 'custom' && serviceEndDate <= serviceStartDate) {
      Alert.alert('Validation Error', 'End date must be after start date');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    try {
      setSubmitting(true);
      
      const updateData: any = {
        category: selectedCategory,
        title: title.trim(),
        description: description.trim(),
        location: location.trim(),
        city: city.trim(),
        preferred_date: preferredDate.toISOString().split('T')[0],
        preferred_time: preferredTime.toTimeString().split(' ')[0].substring(0, 5),
        duration_type: durationType,
        urgency: urgency,
        client_notes: clientNotes.trim() || undefined,
        payment_method: 'pending',
        payment_transaction_id: `PENDING-${Date.now()}`
      };

      if (durationType === 'custom') {
        updateData.service_start_date = serviceStartDate.toISOString().split('T')[0];
        updateData.service_end_date = serviceEndDate.toISOString().split('T')[0];
      }

      await apiService.updateServiceRequest(Number(id), updateData);
      
      Alert.alert(
        'Success',
        'Your service request has been updated successfully!',
        [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
    } catch (error: any) {
      console.error('Error updating service request:', error);
      const errorMessage = error.response?.data?.error || 
                          error.response?.data?.message || 
                          'Failed to update service request';
      Alert.alert('Error', errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Edit Service Request" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>Loading...</Text>
        </View>
      </View>
    );
  }

  if (!request) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Edit Service Request" showBack />
        <View style={styles.errorContainer}>
          <Text style={[styles.errorText, { color: theme.textSecondary }]}>
            Request not found
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Edit Service Request" showBack />
      
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Info Banner */}
        <View style={[styles.infoBanner, { backgroundColor: theme.primary + '15' }]}>
          <Ionicons name="information-circle-outline" size={20} color={theme.primary} />
          <Text style={[styles.infoBannerText, { color: theme.primary }]}>
            Only pending requests can be edited
          </Text>
        </View>

        {/* Category Selection */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Service Category <Text style={styles.required}>*</Text>
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll}>
            {categories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryChip,
                  selectedCategory === category.id && { backgroundColor: theme.primary },
                  selectedCategory !== category.id && { borderColor: theme.border, borderWidth: 1, backgroundColor: theme.card }
                ]}
                onPress={() => setSelectedCategory(category.id)}
              >
                <Text
                  style={[
                    styles.categoryChipText,
                    selectedCategory === category.id ? { color: '#fff' } : { color: theme.text }
                  ]}
                >
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Title */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Title <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
            placeholder="E.g., Fix leaking kitchen faucet"
            placeholderTextColor={theme.textSecondary}
            value={title}
            onChangeText={setTitle}
            maxLength={200}
          />
        </View>

        {/* Description */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Description <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[
              styles.input,
              styles.textArea,
              { backgroundColor: theme.card, color: theme.text, borderColor: theme.border },
            ]}
            placeholder="Describe what you need help with..."
            placeholderTextColor={theme.textSecondary}
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
            maxLength={1000}
          />
        </View>

        {/* Location */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Location <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
            placeholder="Street address or area"
            placeholderTextColor={theme.textSecondary}
            value={location}
            onChangeText={setLocation}
            maxLength={200}
          />
        </View>

        {/* City */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            City <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
            placeholder="City name"
            placeholderTextColor={theme.textSecondary}
            value={city}
            onChangeText={setCity}
            maxLength={100}
          />
        </View>

        {/* Preferred Date */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>Preferred Date</Text>
          <TouchableOpacity
            style={[styles.dateButton, { backgroundColor: theme.card, borderColor: theme.border }]}
            onPress={() => setShowDatePicker(true)}
          >
            <Ionicons name="calendar-outline" size={20} color={theme.primary} />
            <Text style={[styles.dateText, { color: theme.text }]}>{formatDate(preferredDate)}</Text>
          </TouchableOpacity>
          {showDatePicker && (
            <DateTimePicker
              value={preferredDate}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              minimumDate={new Date()}
              onChange={(event, selectedDate) => {
                setShowDatePicker(Platform.OS === 'ios');
                if (selectedDate) setPreferredDate(selectedDate);
              }}
            />
          )}
        </View>

        {/* Preferred Time */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>Preferred Time</Text>
          <TouchableOpacity
            style={[styles.dateButton, { backgroundColor: theme.card, borderColor: theme.border }]}
            onPress={() => setShowTimePicker(true)}
          >
            <Ionicons name="time-outline" size={20} color={theme.primary} />
            <Text style={[styles.dateText, { color: theme.text }]}>{formatTime(preferredTime)}</Text>
          </TouchableOpacity>
          {showTimePicker && (
            <DateTimePicker
              value={preferredTime}
              mode="time"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              onChange={(event, selectedTime) => {
                setShowTimePicker(Platform.OS === 'ios');
                if (selectedTime) setPreferredTime(selectedTime);
              }}
            />
          )}
        </View>

        {/* Estimated Hours */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Service Duration <Text style={styles.required}>*</Text>
          </Text>
          <View style={styles.durationButtons}>
            {[
              { value: 'daily', label: 'Daily' },
              { value: 'monthly', label: 'Monthly' },
              { value: '3_months', label: '3 Months' },
              { value: '6_months', label: '6 Months' },
              { value: 'yearly', label: 'Yearly' },
              { value: 'custom', label: 'Custom' },
            ].map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.durationButton,
                  {
                    backgroundColor: durationType === option.value ? theme.primary : theme.card,
                    borderColor: durationType === option.value ? theme.primary : theme.border,
                  },
                ]}
                onPress={() => setDurationType(option.value as any)}
              >
                <Text
                  style={[
                    styles.durationButtonText,
                    { color: durationType === option.value ? '#FFFFFF' : theme.text },
                  ]}
                >
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Custom Date Range */}
        {durationType === 'custom' && (
          <>
            <View style={styles.section}>
              <Text style={[styles.label, { color: theme.text }]}>
                Start Date <Text style={styles.required}>*</Text>
              </Text>
              <TouchableOpacity
                style={[styles.dateButton, { backgroundColor: theme.card, borderColor: theme.border }]}
                onPress={() => setShowStartDatePicker(true)}
              >
                <Ionicons name="calendar-outline" size={20} color={theme.primary} />
                <Text style={[styles.dateText, { color: theme.text }]}>{formatDate(serviceStartDate)}</Text>
              </TouchableOpacity>
              {showStartDatePicker && (
                <DateTimePicker
                  value={serviceStartDate}
                  mode="date"
                  display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                  minimumDate={new Date()}
                  onChange={(event, selectedDate) => {
                    setShowStartDatePicker(Platform.OS === 'ios');
                    if (selectedDate) setServiceStartDate(selectedDate);
                  }}
                />
              )}
            </View>

            <View style={styles.section}>
              <Text style={[styles.label, { color: theme.text }]}>
                End Date <Text style={styles.required}>*</Text>
              </Text>
              <TouchableOpacity
                style={[styles.dateButton, { backgroundColor: theme.card, borderColor: theme.border }]}
                onPress={() => setShowEndDatePicker(true)}
              >
                <Ionicons name="calendar-outline" size={20} color={theme.primary} />
                <Text style={[styles.dateText, { color: theme.text }]}>{formatDate(serviceEndDate)}</Text>
              </TouchableOpacity>
              {showEndDatePicker && (
                <DateTimePicker
                  value={serviceEndDate}
                  mode="date"
                  display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                  minimumDate={serviceStartDate}
                  onChange={(event, selectedDate) => {
                    setShowEndDatePicker(Platform.OS === 'ios');
                    if (selectedDate) setServiceEndDate(selectedDate);
                  }}
                />
              )}
            </View>
          </>
        )}

        {/* Price Display */}
        {priceCalculation && (
          <View style={[styles.priceCard, { backgroundColor: theme.card, borderColor: theme.primary }]}>
            <View style={styles.priceRow}>
              <Ionicons name="calendar-outline" size={20} color={theme.primary} />
              <Text style={[styles.priceLabel, { color: theme.text }]}>Duration:</Text>
              <Text style={[styles.priceValue, { color: theme.text }]}>
                {priceCalculation.duration_days} days
              </Text>
            </View>
            <View style={styles.priceRow}>
              <Ionicons name="cash-outline" size={20} color={theme.primary} />
              <Text style={[styles.priceLabel, { color: theme.text }]}>Daily Rate:</Text>
              <Text style={[styles.priceValue, { color: theme.text }]}>
                ${priceCalculation.daily_rate}
              </Text>
            </View>
            <View style={[styles.priceRow, styles.totalPriceRow]}>
              <Ionicons name="wallet-outline" size={24} color={theme.primary} />
              <Text style={[styles.totalPriceLabel, { color: theme.text }]}>Total Price:</Text>
              <Text style={[styles.totalPriceValue, { color: theme.primary }]}>
                ${priceCalculation.total_price}
              </Text>
            </View>
          </View>
        )}

        {calculatingPrice && (
          <View style={styles.calculatingContainer}>
            <ActivityIndicator size="small" color={theme.primary} />
            <Text style={[styles.calculatingText, { color: theme.textSecondary }]}>
              Calculating price...
            </Text>
          </View>
        )}

        {/* Urgency */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>Urgency Level</Text>
          <View style={styles.urgencyButtons}>
            {(['normal', 'urgent', 'emergency'] as const).map((level) => (
              <TouchableOpacity
                key={level}
                style={[
                  styles.urgencyButton,
                  {
                    backgroundColor: urgency === level ? getUrgencyColor(level) : theme.card,
                    borderColor: urgency === level ? getUrgencyColor(level) : theme.border,
                  },
                ]}
                onPress={() => setUrgency(level)}
              >
                <Text
                  style={[
                    styles.urgencyButtonText,
                    { color: urgency === level ? '#FFFFFF' : theme.text },
                  ]}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Additional Notes */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>Additional Notes</Text>
          <TextInput
            style={[
              styles.input,
              styles.textArea,
              { backgroundColor: theme.card, color: theme.text, borderColor: theme.border },
            ]}
            placeholder="Any additional information..."
            placeholderTextColor={theme.textSecondary}
            value={clientNotes}
            onChangeText={setClientNotes}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
            maxLength={500}
          />
        </View>

        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.cancelButton, { backgroundColor: theme.card, borderColor: theme.border }]}
            onPress={() => router.back()}
            disabled={submitting}
          >
            <Text style={[styles.cancelButtonText, { color: theme.text }]}>Cancel</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.submitButton,
              { backgroundColor: submitting ? theme.textSecondary : theme.primary },
            ]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={20} color="#FFFFFF" />
                <Text style={styles.submitButtonText}>Update Request</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </View>
  );
}

function getUrgencyColor(urgency: string): string {
  switch (urgency) {
    case 'normal':
      return '#4CAF50';
    case 'urgent':
      return '#FFA500';
    case 'emergency':
      return '#F44336';
    default:
      return '#757575';
  }
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
    padding: 16,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  infoBannerText: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  section: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  required: {
    color: '#F44336',
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
  },
  textArea: {
    minHeight: 100,
    paddingTop: 12,
  },
  dateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 8,
  },
  dateText: {
    fontSize: 16,
    flex: 1,
  },
  urgencyButtons: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  urgencyButton: {
    flex: 1,
    minWidth: '22%',
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  urgencyButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  durationButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  durationButton: {
    flex: 1,
    minWidth: '30%',
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  durationButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  priceCard: {
    borderWidth: 2,
    borderRadius: 12,
    padding: 16,
    marginVertical: 12,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  priceLabel: {
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  priceValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  totalPriceRow: {
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  totalPriceLabel: {
    fontSize: 16,
    fontWeight: '700',
    flex: 1,
  },
  totalPriceValue: {
    fontSize: 24,
    fontWeight: '700',
  },
  calculatingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    gap: 8,
  },
  calculatingText: {
    fontSize: 14,
    fontStyle: 'italic',
  },
  categoryScroll: {
    maxHeight: 100,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    marginRight: 8,
    marginBottom: 8,
  },
  categoryChipText: {
    fontSize: 14,
    fontWeight: '600',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  submitButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: 8,
    gap: 8,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  bottomSpacer: {
    height: 40,
  },
});
