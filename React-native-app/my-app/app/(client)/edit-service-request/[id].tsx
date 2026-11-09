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
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useTranslation } from 'react-i18next';

const URGENCY_OPTIONS = [
  { value: 'normal', label: 'requestService.normal' },
  { value: 'urgent', label: 'requestService.urgent' },
  { value: 'emergency', label: 'requestService.emergency' },
];

export default function EditServiceRequestScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams();
  const { theme } = useTheme();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [city, setCity] = useState('');
  const [urgency, setUrgency] = useState<'normal' | 'urgent' | 'emergency'>('normal');
  const [clientNotes, setClientNotes] = useState('');
  const [workersNeeded, setWorkersNeeded] = useState(1);
  const [preferredDate, setPreferredDate] = useState<Date>(new Date());
  const [preferredTime, setPreferredTime] = useState<Date>(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);

  useEffect(() => {
    loadRequest();
  }, [id]);

  const loadRequest = async () => {
    try {
      setLoading(true);
      const response = await apiService.getServiceRequestDetail(Number(id));
      const req = response.service_request || response;

      setTitle(req.title || '');
      setDescription(req.description || '');
      setLocation(req.location || '');
      setCity(req.city || '');
      setUrgency(req.urgency || 'normal');
      setClientNotes(req.client_notes || '');
      setWorkersNeeded(req.workers_needed || 1);

      if (req.preferred_date) {
        const [year, month, day] = req.preferred_date.split('-').map(Number);
        setPreferredDate(new Date(year, month - 1, day));
      }
      if (req.preferred_time) {
        const [hours, minutes] = req.preferred_time.split(':').map(Number);
        const t = new Date();
        t.setHours(hours, minutes, 0, 0);
        setPreferredTime(t);
      }
    } catch (error: any) {
      Alert.alert(t('common.error'), t('requestDetail.failedLoad'));
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterTitle'));
      return;
    }
    if (!description.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterDescription'));
      return;
    }
    if (!location.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterLocationField'));
      return;
    }
    if (!city.trim()) {
      Alert.alert(t('client.validationError'), t('requestService.enterCityField'));
      return;
    }

    try {
      setSubmitting(true);
      await apiService.updateServiceRequest(Number(id), {
        title: title.trim(),
        description: description.trim(),
        location: location.trim(),
        city: city.trim(),
        urgency,
        client_notes: clientNotes.trim(),
        workers_needed: workersNeeded,
        preferred_date: preferredDate.toISOString().split('T')[0],
        preferred_time: preferredTime.toTimeString().split(' ')[0].substring(0, 5),
      });

      Alert.alert(t('common.success'), t('editRequest.updatedSuccess'), [
        { text: t('common.ok'), onPress: () => router.back() },
      ]);
    } catch (error: any) {
      const msg = error.response?.data?.error || error.response?.data?.message || t('editRequest.failedUpdate');
      Alert.alert(t('common.error'), msg);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (date: Date) =>
    date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  const formatTime = (date: Date) =>
    date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title={t('editRequest.title')} showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>{t('common.loading')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title={t('editRequest.title')} showBack />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView style={styles.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">

          {/* Title */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('editRequest.titleLabel')} <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={title}
              onChangeText={setTitle}
              placeholder={t('editRequest.titlePlaceholder')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          {/* Description */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('editRequest.descriptionLabel')} <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={[styles.input, styles.textArea, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={description}
              onChangeText={setDescription}
              placeholder={t('editRequest.descriptionPlaceholder')}
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
          </View>

          {/* Location */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('profile.location')} <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={location}
              onChangeText={setLocation}
              placeholder={t('editRequest.locationPlaceholder')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          {/* City */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('profile.city')} <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={city}
              onChangeText={setCity}
              placeholder={t('profile.city')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          {/* Preferred Date */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('requestService.preferredDate')}</Text>
            <TouchableOpacity
              style={[styles.input, styles.pickerRow, { backgroundColor: theme.card, borderColor: theme.border }]}
              onPress={() => setShowDatePicker(true)}
            >
              <Ionicons name="calendar-outline" size={18} color={theme.primary} />
              <Text style={[styles.pickerText, { color: theme.text }]}>{formatDate(preferredDate)}</Text>
            </TouchableOpacity>
            {showDatePicker && (
              <DateTimePicker
                value={preferredDate}
                mode="date"
                display="default"
                minimumDate={new Date()}
                onChange={(_, date) => { setShowDatePicker(false); if (date) setPreferredDate(date); }}
              />
            )}
          </View>

          {/* Preferred Time */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('requestService.preferredTime')}</Text>
            <TouchableOpacity
              style={[styles.input, styles.pickerRow, { backgroundColor: theme.card, borderColor: theme.border }]}
              onPress={() => setShowTimePicker(true)}
            >
              <Ionicons name="time-outline" size={18} color={theme.primary} />
              <Text style={[styles.pickerText, { color: theme.text }]}>{formatTime(preferredTime)}</Text>
            </TouchableOpacity>
            {showTimePicker && (
              <DateTimePicker
                value={preferredTime}
                mode="time"
                display="default"
                onChange={(_, time) => { setShowTimePicker(false); if (time) setPreferredTime(time); }}
              />
            )}
          </View>

          {/* Urgency */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('editRequest.urgency')}</Text>
            <View style={styles.urgencyRow}>
              {URGENCY_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt.value}
                  style={[
                    styles.urgencyBtn,
                    {
                      backgroundColor: urgency === opt.value ? theme.primary : theme.card,
                      borderColor: urgency === opt.value ? theme.primary : theme.border,
                    },
                  ]}
                  onPress={() => setUrgency(opt.value as any)}
                >
                  <Text style={{ color: urgency === opt.value ? '#fff' : theme.text, fontSize: 13, fontFamily: 'Poppins_500Medium' }}>
                    {t(opt.label)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Workers Needed */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('editRequest.workersNeeded')}</Text>
            <View style={styles.counterRow}>
              <TouchableOpacity
                style={[styles.counterBtn, { backgroundColor: theme.card, borderColor: theme.border }]}
                onPress={() => setWorkersNeeded(Math.max(1, workersNeeded - 1))}
              >
                <Ionicons name="remove" size={20} color={theme.primary} />
              </TouchableOpacity>
              <Text style={[styles.counterValue, { color: theme.text }]}>{workersNeeded}</Text>
              <TouchableOpacity
                style={[styles.counterBtn, { backgroundColor: theme.card, borderColor: theme.border }]}
                onPress={() => setWorkersNeeded(workersNeeded + 1)}
              >
                <Ionicons name="add" size={20} color={theme.primary} />
              </TouchableOpacity>
            </View>
          </View>

          {/* Client Notes */}
          <View style={styles.section}>
            <Text style={[styles.label, { color: theme.text }]}>{t('requestService.additionalNotes')}</Text>
            <TextInput
              style={[styles.input, styles.textArea, { backgroundColor: theme.card, color: theme.text, borderColor: theme.border }]}
              value={clientNotes}
              onChangeText={setClientNotes}
              placeholder={t('editRequest.notesPlaceholder')}
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>

          {/* Submit Button */}
          <TouchableOpacity
            style={[styles.submitBtn, { backgroundColor: theme.primary, opacity: submitting ? 0.7 : 1 }]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={20} color="#fff" />
                <Text style={styles.submitText}>{t('client.saveChanges')}</Text>
              </>
            )}
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 14, fontFamily: 'Poppins_400Regular' },
  content: { flex: 1, paddingHorizontal: 16 },
  section: { marginTop: 16 },
  label: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  required: { color: '#EF4444' },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  textArea: { minHeight: 90, paddingTop: 12 },
  pickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  pickerText: { fontSize: 14, fontFamily: 'Poppins_400Regular' },
  urgencyRow: { flexDirection: 'row', gap: 10 },
  urgencyBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
  },
  counterRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  counterBtn: {
    width: 42,
    height: 42,
    borderRadius: 10,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  counterValue: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', minWidth: 30, textAlign: 'center' },
  submitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 24,
    paddingVertical: 14,
    borderRadius: 12,
  },
  submitText: { color: '#fff', fontSize: 16, fontFamily: 'Poppins_600SemiBold' },
});
