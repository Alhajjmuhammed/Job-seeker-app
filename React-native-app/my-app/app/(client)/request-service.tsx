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
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import PaymentModal from '../../components/PaymentModal';
import apiService from '../../services/api';
import DateTimePicker from '@react-native-community/datetimepicker';

interface Category {
  id: number;
  name: string;
  description: string;
  daily_rate?: number;
}

interface PriceCalculation {
  duration_days: number;
  daily_rate: number;
  total_price: number;
  duration_type_display: string;
}

export default function RequestServiceScreen() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  
  // Payment modal state
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  
  // Form state
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [city, setCity] = useState('');
  const [preferredDate, setPreferredDate] = useState<Date>(new Date());
  const [preferredTime, setPreferredTime] = useState<Date>(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  
  // NEW: Duration & Pricing state
  const [durationType, setDurationType] = useState<'daily' | 'monthly' | '3_months' | '6_months' | 'yearly' | 'custom'>('daily');
  const [serviceStartDate, setServiceStartDate] = useState<Date>(new Date());
  const [serviceEndDate, setServiceEndDate] = useState<Date>(new Date());
  const [showStartDatePicker, setShowStartDatePicker] = useState(false);
  const [showEndDatePicker, setShowEndDatePicker] = useState(false);
  const [priceCalculation, setPriceCalculation] = useState<PriceCalculation | null>(null);
  const [calculatingPrice, setCalculatingPrice] = useState(false);
  
  const [urgency, setUrgency] = useState<'normal' | 'urgent' | 'emergency'>('normal');
  const [clientNotes, setClientNotes] = useState('');

  const resetForm = () => {
    setSelectedCategory(null);
    setTitle('');
    setDescription('');
    setLocation('');
    setCity('');
    setPreferredDate(new Date());
    setPreferredTime(new Date());
    setDurationType('daily');
    setServiceStartDate(new Date());
    setServiceEndDate(new Date());
    setUrgency('normal');
    setClientNotes('');
    setPriceCalculation(null);
  };

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const response = await apiService.getCategoryPricing();
      setCategories(response.categories || []);
    } catch (error: any) {
      console.error('Error loading categories:', error);
      Alert.alert('Error', 'Failed to load service categories');
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

  // NEW: Calculate price when duration or category changes
  useEffect(() => {
    if (selectedCategory) {
      calculatePrice();
    }
  }, [selectedCategory, calculatePrice]);

  const handlePayAndSubmit = async () => {
    if (!validateForm()) return;
    
    // Show payment modal instead of submitting directly
    setShowPaymentModal(true);
  };

  const handlePaymentSuccess = async (paymentData: any) => {
    try {
      setSubmitting(true);
      setShowPaymentModal(false);

      // Submit service request with actual payment data
      const requestData: any = {
        category: selectedCategory!,
        title: title.trim(),
        description: description.trim(),
        location: location.trim(),
        city: city.trim(),
        preferred_date: preferredDate.toISOString().split('T')[0],
        preferred_time: preferredTime.toTimeString().split(' ')[0].substring(0, 5),
        duration_type: durationType,
        urgency: urgency,
        client_notes: clientNotes.trim() || undefined,
        payment_method: paymentData.payment_method,
        payment_transaction_id: paymentData.transaction_id
      };

      if (durationType === 'custom') {
        requestData.service_start_date = serviceStartDate.toISOString().split('T')[0];
        requestData.service_end_date = serviceEndDate.toISOString().split('T')[0];
      }

      await apiService.requestService(selectedCategory!, requestData);
      
      // Reset form fields
      resetForm();
      
      Alert.alert(
        'Success!',
        `Your service request has been submitted and payment of TSH ${priceCalculation!.total_price.toFixed(2)} has been processed! Our admin will assign a qualified worker soon.`,
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
      console.error('Error:', error);
      const errorMessage = error.response?.data?.error || 
                          error.response?.data?.message || 
                          'Failed to submit request. Please try again.';
      Alert.alert('Error', errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  function validateForm(): boolean {
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
        <Header title="Request Service" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>Loading...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Request Service" showBack />
      
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Category Selection */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Service Category <Text style={styles.required}>*</Text>
          </Text>
          <View style={styles.categoryGrid}>
            {categories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryCard,
                  { 
                    backgroundColor: selectedCategory === category.id ? theme.primary : theme.card,
                    borderColor: selectedCategory === category.id ? theme.primary : theme.border,
                  },
                ]}
                onPress={() => setSelectedCategory(category.id)}
              >
                <Text
                  style={[
                    styles.categoryName,
                    { color: selectedCategory === category.id ? '#FFFFFF' : theme.text },
                  ]}
                >
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
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

        {/* Price Calculation Display */}
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
                TSH {priceCalculation.daily_rate}
              </Text>
            </View>
            <View style={[styles.priceRow, styles.totalPriceRow]}>
              <Ionicons name="wallet-outline" size={24} color={theme.primary} />
              <Text style={[styles.totalPriceLabel, { color: theme.text }]}>Total Price:</Text>
              <Text style={[styles.totalPriceValue, { color: theme.primary }]}>
                TSH {priceCalculation.total_price}
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

        {/* Single Submit Button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            { backgroundColor: submitting ? theme.textSecondary : '#4CAF50' },
          ]}
          onPress={handlePayAndSubmit}
          disabled={submitting || !priceCalculation}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="card-outline" size={24} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>
                Pay TSH {priceCalculation?.total_price || '0'} to Get Service
              </Text>
            </>
          )}
        </TouchableOpacity>

        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Payment Modal */}
      <PaymentModal
        visible={showPaymentModal}
        amount={priceCalculation?.total_price || 0}
        currency="TSH"
        onClose={() => setShowPaymentModal(false)}
        onPaymentSuccess={handlePaymentSuccess}
        processPayment={apiService.processPayment.bind(apiService)}
      />
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
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  required: {
    color: '#F44336',
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  categoryCard: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    minWidth: '30%',
  },
  categoryName: {
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
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
  durationButtons: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  durationButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    minWidth: '30%',
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
    marginBottom: 16,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  priceLabel: {
    fontSize: 14,
    flex: 1,
  },
  priceValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  totalPriceRow: {
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  totalPriceLabel: {
    fontSize: 18,
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
    padding: 12,
    gap: 8,
  },
  calculatingText: {
    fontSize: 14,
  },
  paymentButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 8,
    gap: 8,
    marginTop: 8,
  },
  paymentButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
  },
  demoNote: {
    fontSize: 12,
    textAlign: 'center',
    marginTop: 8,
    fontStyle: 'italic',
  },
  paymentSuccess: {
    alignItems: 'center',
    padding: 24,
    borderRadius: 12,
    gap: 8,
  },
  paymentSuccessText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4CAF50',
  },
  transactionId: {
    fontSize: 12,
    color: '#666',
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
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 8,
    gap: 8,
    marginTop: 8,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
  },
  bottomSpacer: {
    height: 40,
  },
});
