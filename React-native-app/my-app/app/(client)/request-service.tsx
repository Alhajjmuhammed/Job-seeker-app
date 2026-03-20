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
import PaymentScreenshotModal from '../../components/PaymentScreenshotModal';
import apiService from '../../services/api';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useTranslation } from 'react-i18next';

interface Category {
  id: number;
  name: string;
  description: string;
  daily_rate?: number;
}

interface PriceCalculation {
  duration_days: number;
  daily_rate: number;
  workers_needed: number;
  total_price: number;
  duration_type_display: string;
}

export default function RequestServiceScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  
  // Payment modal state
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showScreenshotModal, setShowScreenshotModal] = useState(false);
  const [paymentData, setPaymentData] = useState<any>(null);
  
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
  const [workersNeeded, setWorkersNeeded] = useState<number>(1); // NEW: Number of workers needed
  const [availableWorkers, setAvailableWorkers] = useState<number>(0); // Worker availability

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
    setWorkersNeeded(1);
    setPriceCalculation(null);
    setPaymentData(null);
    setShowScreenshotModal(false);
    setShowPaymentModal(false);
    setAvailableWorkers(0);
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
      Alert.alert(t('common.error'), t('requestService.failedLoadCategories'));
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
        workers_needed: workersNeeded,
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
  }, [selectedCategory, durationType, serviceStartDate, serviceEndDate, workersNeeded]);

  // NEW: Calculate price when duration or category changes
  useEffect(() => {
    if (selectedCategory) {
      calculatePrice();
      fetchWorkerAvailability();
    }
  }, [selectedCategory, calculatePrice]);

  // Fetch worker availability when category is selected
  const fetchWorkerAvailability = async () => {
    if (!selectedCategory) {
      setAvailableWorkers(0);
      return;
    }
    
    try {
      const servicesResponse = await apiService.getServices();
      const serviceData = servicesResponse.services?.find((s: any) => s.id === selectedCategory);
      if (serviceData && typeof serviceData.available_workers === 'number') {
        setAvailableWorkers(serviceData.available_workers);
      } else {
        setAvailableWorkers(0);
      }
    } catch (error) {
      console.error('Error loading worker availability:', error);
      setAvailableWorkers(0);
    }
  };

  const handlePayAndSubmit = async () => {
    if (!validateForm()) return;
    
    // Check worker availability before proceeding to payment
    const selectedCat = categories.find(c => c.id === selectedCategory);
    const categoryName = selectedCat?.name || 'this service';
    
    if (availableWorkers === 0) {
      Alert.alert(
        '⚠️ No Workers Available',
        `There are currently no available workers for ${categoryName}.\n\nYour request will be queued and processed when workers become available.\n\nDo you want to proceed anyway?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'Proceed Anyway', 
            onPress: () => setShowPaymentModal(true),
            style: 'default'
          }
        ]
      );
    } else if (workersNeeded > availableWorkers) {
      Alert.alert(
        'ℹ️ Limited Availability',
        `You requested ${workersNeeded} worker(s), but only ${availableWorkers} are currently available.\n\nYour request will be accepted and prioritized.\n\nDo you want to continue?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'Continue', 
            onPress: () => setShowPaymentModal(true),
            style: 'default'
          }
        ]
      );
    } else {
      // Sufficient workers available - proceed directly
      setShowPaymentModal(true);
    }
  };

  const handlePaymentSuccess = async (transactionData: any) => {
    // Store payment data and show screenshot upload modal
    console.log('handlePaymentSuccess called with:', transactionData);
    console.log('Current modals state - payment:', showPaymentModal, 'screenshot:', showScreenshotModal);
    
    setPaymentData(transactionData);
    
    // Use setTimeout to ensure state updates happen in sequence
    setTimeout(() => {
      setShowPaymentModal(false);
      setTimeout(() => {
        setShowScreenshotModal(true);
        console.log('Screenshot modal should now be visible');
      }, 100);
    }, 100);
    
    console.log('Modals updated - payment should close, screenshot should open');
  };

  const handleScreenshotSubmit = async (screenshot: any) => {
    try {
      setSubmitting(true);

      // Submit service request with payment data and screenshot
      const formData = new FormData();
      formData.append('category', selectedCategory!.toString());
      formData.append('title', title.trim());
      formData.append('description', description.trim());
      formData.append('location', location.trim());
      formData.append('city', city.trim());
      formData.append('preferred_date', preferredDate.toISOString().split('T')[0]);
      formData.append('preferred_time', preferredTime.toTimeString().split(' ')[0].substring(0, 5));
      formData.append('duration_type', durationType);
      formData.append('workers_needed', workersNeeded.toString());
      formData.append('urgency', urgency);
      if (clientNotes.trim()) {
        formData.append('client_notes', clientNotes.trim());
      }
      formData.append('payment_method', paymentData.payment_method);
      formData.append('payment_transaction_id', paymentData.transaction_id);

      if (durationType === 'custom') {
        formData.append('service_start_date', serviceStartDate.toISOString().split('T')[0]);
        formData.append('service_end_date', serviceEndDate.toISOString().split('T')[0]);
      }

      // Add screenshot if provided
      if (screenshot) {
        const localUri = screenshot.uri;
        const filename = localUri.split('/').pop() || 'payment_screenshot.jpg';
        const match = /\.(\w+)$/.exec(filename);
        const type = match ? `image/${match[1]}` : 'image/jpeg';

        formData.append('payment_screenshot', {
          uri: localUri,
          name: filename,
          type,
        } as any);
      }

      await apiService.requestService(selectedCategory!, formData);
      
      // Close modal and reset everything
      setShowScreenshotModal(false);
      setPaymentData(null);
      resetForm();
      
      Alert.alert(
        'Success!',
        `Your service request has been submitted and payment of TSH ${priceCalculation!.total_price.toFixed(2)} has been processed! Our admin will review your payment and assign a qualified worker soon.`,
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
      Alert.alert(t('common.error'), errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleScreenshotSkip = () => {
    // Submit without screenshot
    handleScreenshotSubmit(null);
  };

  const handleScreenshotModalClose = () => {
    // Clear payment data and close modal
    setShowScreenshotModal(false);
    setPaymentData(null);
  };

  function validateForm(): boolean {
    if (!selectedCategory) {
      Alert.alert(t('client.validationError'), t('requestService.selectCategory'));
      return false;
    }
    if (!title.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterTitle'));
      return false;
    }
    if (!description.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterDescription'));
      return false;
    }
    if (!location.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterLocationField'));
      return false;
    }
    if (!city.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterCityField'));
      return false;
    }
    if (!priceCalculation) {
      Alert.alert(t('common.error'), t('requestService.priceCalculationRequired'));
      return false;
    }
    if (durationType === 'custom' && serviceEndDate <= serviceStartDate) {
      Alert.alert(t('client.validationError'), t('requestService.endDateAfterStart'));
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
          <Text style={[styles.loadingText, { color: theme.text }]}>{t('common.loading')}</Text>
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

        {/* Worker Availability Info - Show After Category Selection */}
        {selectedCategory && (
          availableWorkers === 0 ? (
            <View style={[styles.warningCard, { backgroundColor: '#FEF3C7', borderColor: '#F59E0B' }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="warning" size={24} color="#F59E0B" />
                <Text style={[styles.warningTitle, { color: '#92400E' }]}>{t('requestService.noWorkersAvailable')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#78350F' }]}>
                There are currently no available workers for {categories.find(c => c.id === selectedCategory)?.name}.
                Your request will be queued and processed as soon as workers become available.
              </Text>
            </View>
          ) : availableWorkers < 5 ? (
            <View style={[styles.warningCard, { backgroundColor: '#E0F2FE', borderColor: '#0EA5E9' }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="information-circle" size={24} color="#0EA5E9" />
                <Text style={[styles.warningTitle, { color: '#0C4A6E' }]}>{t('requestService.limitedAvailability')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#075985' }]}>
                Only {availableWorkers} worker(s) currently available for {categories.find(c => c.id === selectedCategory)?.name}.
                Your request will be prioritized.
              </Text>
            </View>
          ) : (
            <View style={[styles.warningCard, { backgroundColor: '#D1FAE5', borderColor: '#10B981' }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="checkmark-circle" size={24} color="#10B981" />
                <Text style={[styles.warningTitle, { color: '#065F46' }]}>{t('search.workersAvailableCount')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#047857' }]}>
                {availableWorkers} worker(s) available for {categories.find(c => c.id === selectedCategory)?.name}.
                Your request will be processed quickly.
              </Text>
            </View>
          )
        )}

        {/* Title */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Title <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
            placeholder={t('requestService.titlePlaceholder')}
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
            placeholder={t('requestService.descriptionPlaceholder')}
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
            placeholder={t('requestService.locationStreet')}
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
            placeholder={t('requestService.cityName')}
            placeholderTextColor={theme.textSecondary}
            value={city}
            onChangeText={setCity}
            maxLength={100}
          />
        </View>

        {/* Preferred Date */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>{t('requestService.preferredDate')}</Text>
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
          <Text style={[styles.label, { color: theme.text }]}>{t('requestService.preferredTime')}</Text>
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

        {/* Number of Workers Needed */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>
            Number of Workers Needed <Text style={styles.required}>*</Text>
          </Text>
          <View style={styles.workersSelector}>
            <TouchableOpacity
              style={[styles.workerButton, { backgroundColor: theme.card, borderColor: theme.border }]}
              onPress={() => setWorkersNeeded(Math.max(1, workersNeeded - 1))}
              disabled={workersNeeded <= 1}
            >
              <Ionicons name="remove" size={20} color={workersNeeded <= 1 ? theme.textSecondary : theme.primary} />
            </TouchableOpacity>
            <View style={[styles.workersCount, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <Text style={[styles.workersCountText, { color: theme.text }]}>{workersNeeded}</Text>
            </View>
            <TouchableOpacity
              style={[styles.workerButton, { backgroundColor: theme.card, borderColor: theme.border }]}
              onPress={() => setWorkersNeeded(Math.min(100, workersNeeded + 1))}
              disabled={workersNeeded >= 100}
            >
              <Ionicons name="add" size={20} color={workersNeeded >= 100 ? theme.textSecondary : theme.primary} />
            </TouchableOpacity>
          </View>
          <Text style={[styles.helperText, { color: theme.textSecondary }]}>
            💡 {workersNeeded} {workersNeeded === 1 ? 'worker' : 'workers'} × duration × rate
          </Text>
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
            <View style={styles.priceHeader}>
              <Ionicons name="calculator-outline" size={24} color={theme.primary} />
              <Text style={[styles.priceHeaderText, { color: theme.text }]}>{t('requestService.priceBreakdown')}</Text>
            </View>
            
            <View style={styles.priceRow}>
              <Ionicons name="people-outline" size={20} color={theme.primary} />
              <Text style={[styles.priceLabel, { color: theme.text }]}>{t('requestService.workers')}</Text>
              <Text style={[styles.priceValue, { color: theme.text }]}>
                {priceCalculation.workers_needed || workersNeeded}
              </Text>
            </View>
            
            <View style={styles.priceRow}>
              <Ionicons name="calendar-outline" size={20} color={theme.primary} />
              <Text style={[styles.priceLabel, { color: theme.text }]}>{t('requestService.duration')}</Text>
              <Text style={[styles.priceValue, { color: theme.text }]}>
                {priceCalculation.duration_days} days
              </Text>
            </View>
            
            <View style={styles.priceRow}>
              <Ionicons name="cash-outline" size={20} color={theme.primary} />
              <Text style={[styles.priceLabel, { color: theme.text }]}>{t('requestService.rateDayWorker')}</Text>
              <Text style={[styles.priceValue, { color: theme.text }]}>
                TSH {priceCalculation.daily_rate.toLocaleString()}
              </Text>
            </View>
            
            <View style={styles.priceDivider} />
            
            <View style={[styles.priceRow, styles.totalPriceRow]}>
              <Ionicons name="wallet-outline" size={24} color={theme.primary} />
              <Text style={[styles.totalPriceLabel, { color: theme.text }]}>{t('requestService.totalPrice')}</Text>
              <Text style={[styles.totalPriceValue, { color: theme.primary }]}>
                TSH {priceCalculation.total_price.toLocaleString()}
              </Text>
            </View>
            
            <Text style={[styles.priceFormula, { color: theme.textSecondary }]}>
              💡 {priceCalculation.workers_needed || workersNeeded} workers × {priceCalculation.duration_days} days × TSH {priceCalculation.daily_rate.toLocaleString()} = TSH {priceCalculation.total_price.toLocaleString()}
            </Text>
          </View>
        )}

        {calculatingPrice && (
          <View style={styles.calculatingContainer}>
            <ActivityIndicator size="small" color={theme.primary} />
            <Text style={[styles.calculatingText, { color: theme.textSecondary }]}>{t('requestService.calculatingPrice')}</Text>
          </View>
        )}

        {/* Urgency */}
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.text }]}>{t('requestService.urgencyLevel')}</Text>
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
          <Text style={[styles.label, { color: theme.text }]}>{t('requestService.additionalNotes')}</Text>
          <TextInput
            style={[
              styles.input,
              styles.textArea,
              { backgroundColor: theme.card, color: theme.text, borderColor: theme.border },
            ]}
            placeholder={t('requestService.anyAdditionalInfo')}
            placeholderTextColor={theme.textSecondary}
            value={clientNotes}
            onChangeText={setClientNotes}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
            maxLength={500}
          />
        </View>

        {/* Worker Availability Info - Always Show Before Submit */}
        {selectedCategory && (
          availableWorkers === 0 ? (
            <View style={[styles.warningCard, { backgroundColor: '#FEF3C7', borderColor: '#F59E0B', marginTop: 16, marginBottom: 8 }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="warning" size={24} color="#F59E0B" />
                <Text style={[styles.warningTitle, { color: '#92400E' }]}>{t('requestService.noWorkersAvailableSymbol')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#78350F' }]}>
                No available workers for {categories.find(c => c.id === selectedCategory)?.name}. Your request will be queued.
              </Text>
            </View>
          ) : availableWorkers < 5 ? (
            <View style={[styles.warningCard, { backgroundColor: '#E0F2FE', borderColor: '#0EA5E9', marginTop: 16, marginBottom: 8 }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="information-circle" size={24} color="#0EA5E9" />
                <Text style={[styles.warningTitle, { color: '#0C4A6E' }]}>{t('requestService.limitedAvailabilitySymbol')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#075985' }]}>
                Only {availableWorkers} worker(s) available. Request will be prioritized.
              </Text>
            </View>
          ) : (
            <View style={[styles.warningCard, { backgroundColor: '#D1FAE5', borderColor: '#10B981', marginTop: 16, marginBottom: 8 }]}>
              <View style={styles.warningHeader}>
                <Ionicons name="checkmark-circle" size={24} color="#10B981" />
                <Text style={[styles.warningTitle, { color: '#065F46' }]}>{t('requestService.workersAvailableSymbol')}</Text>
              </View>
              <Text style={[styles.warningText, { color: '#047857' }]}>
                {availableWorkers} worker(s) available for {categories.find(c => c.id === selectedCategory)?.name}. Your request will be processed quickly.
              </Text>
            </View>
          )
        )}

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

      {/* Payment Screenshot Modal */}
      <PaymentScreenshotModal
        visible={showScreenshotModal}
        paymentData={paymentData}
        onClose={handleScreenshotModalClose}
        onSubmit={handleScreenshotSubmit}
        onSkip={handleScreenshotSkip}
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
    marginBottom: 20,
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
  workersSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginVertical: 8,
  },
  workerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  workersCount: {
    minWidth: 80,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  workersCountText: {
    fontSize: 24,
    fontWeight: '700',
  },
  workersLabel: {
    fontSize: 12,
    marginTop: 4,
  },
  helperText: {
    fontSize: 11,
    marginTop: 6,
    textAlign: 'center',
  },
  priceCard: {
    borderWidth: 2,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  priceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  priceHeaderText: {
    fontSize: 18,
    fontWeight: '700',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
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
  priceDivider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 8,
  },
  totalPriceRow: {
    marginTop: 8,
    paddingTop: 4,
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
  priceFormula: {
    fontSize: 12,
    marginTop: 12,
    textAlign: 'center',
    lineHeight: 18,
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
  warningCard: {
    borderRadius: 12,
    borderWidth: 2,
    padding: 16,
    marginHorizontal: 0,
  },
  warningHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  warningText: {
    fontSize: 14,
    lineHeight: 20,
  },
  bottomSpacer: {
    height: 40,
  },
});
