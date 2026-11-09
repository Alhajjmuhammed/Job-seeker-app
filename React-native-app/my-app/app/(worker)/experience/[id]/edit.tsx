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
  Switch,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../../contexts/ThemeContext';
import Header from '../../../../components/Header';
import apiService from '../../../../services/api';
// @ts-ignore - Package is installed but TypeScript may not resolve types immediately
import DateTimePicker from '@react-native-community/datetimepicker';
import { useTranslation } from 'react-i18next';

export default function EditExperienceScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Form fields
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [location, setLocation] = useState('');
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date());
  const [isCurrent, setIsCurrent] = useState(false);
  const [description, setDescription] = useState('');
  
  // Date picker visibility
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);

  // This screen stays mounted between visits: reload whenever a different item is opened.
  useEffect(() => {
    loadExperience();
  }, [id]);

  const loadExperience = async () => {
    try {
      setLoading(true);
      const experiences = await apiService.getWorkExperiences();
      const experience = experiences.find((exp: any) => exp.id === parseInt(id as string));
      
      if (!experience) {
        Alert.alert(t('common.error'), t('experienceScreen.notFound'), [
          { text: t('common.ok'), onPress: () => router.back() }
        ]);
        return;
      }

      setJobTitle(experience.job_title);
      setCompany(experience.company);
      setLocation(experience.location || '');
      setStartDate(new Date(experience.start_date));
      setEndDate(experience.end_date ? new Date(experience.end_date) : new Date());
      setIsCurrent(experience.is_current);
      setDescription(experience.description || '');
    } catch (error) {
      console.error('Failed to load experience:', error);
      Alert.alert(t('common.error'), t('experienceScreen.failedLoad'), [
        { text: t('common.ok'), onPress: () => router.back() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validation
    if (!jobTitle.trim()) {
      Alert.alert(t('client.validationError'), t('experienceScreen.jobTitleRequired'));
      return;
    }
    if (!company.trim()) {
      Alert.alert(t('client.validationError'), t('experienceScreen.companyRequired'));
      return;
    }

    try {
      setSaving(true);
      
      const data = {
        job_title: jobTitle,
        company: company,
        location: location,
        start_date: startDate.toISOString().split('T')[0],
        end_date: isCurrent ? null : endDate.toISOString().split('T')[0],
        is_current: isCurrent,
        description: description,
      };

      await apiService.updateWorkExperience(parseInt(id as string), data);
      Alert.alert(t('common.success'), t('experienceScreen.updatedSuccess'), [
        { text: t('common.ok'), onPress: () => router.back() }
      ]);
    } catch (error: any) {
      console.error('Failed to update experience:', error);
      Alert.alert(t('common.error'), error.response?.data?.error || t('experienceScreen.failedUpdate'));
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header showBack />
        <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>{t('experienceScreen.loadingOne')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      
      <Header showBack />

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.text }]}>{t('experienceScreen.editTitle')}</Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
            {t('experienceScreen.editSubtitle')}
          </Text>
        </View>

        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>
              {t('experienceScreen.jobTitle')} <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={jobTitle}
              onChangeText={setJobTitle}
              placeholder={t('experienceScreen.jobTitlePlaceholder')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>
              {t('experienceScreen.company')} <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={company}
              onChangeText={setCompany}
              placeholder={t('experienceScreen.companyPlaceholder')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>{t('jobs.location')}</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={location}
              onChangeText={setLocation}
              placeholder={t('experienceScreen.locationPlaceholder')}
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.formRow}>
            <View style={styles.formGroupHalf}>
              <Text style={[styles.label, { color: theme.text }]}>{t('experienceScreen.startDate')}</Text>
              <TouchableOpacity
                style={[styles.dateButton, { backgroundColor: theme.surface, borderColor: theme.border }]}
                onPress={() => setShowStartPicker(true)}
              >
                <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
                <Text style={[styles.dateButtonText, { color: theme.text }]}>
                  {formatDate(startDate)}
                </Text>
              </TouchableOpacity>
            </View>

            {!isCurrent && (
              <View style={styles.formGroupHalf}>
                <Text style={[styles.label, { color: theme.text }]}>{t('experienceScreen.endDate')}</Text>
                <TouchableOpacity
                  style={[styles.dateButton, { backgroundColor: theme.surface, borderColor: theme.border }]}
                  onPress={() => setShowEndPicker(true)}
                >
                  <Ionicons name="calendar-outline" size={20} color={theme.textSecondary} />
                  <Text style={[styles.dateButtonText, { color: theme.text }]}>
                    {formatDate(endDate)}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          <View style={styles.formGroup}>
            <View style={styles.checkboxContainer}>
              <Switch
                value={isCurrent}
                onValueChange={setIsCurrent}
                trackColor={{ false: theme.border, true: theme.primary }}
                thumbColor="#FFFFFF"
              />
              <Text style={[styles.checkboxLabel, { color: theme.text }]}>
                {t('experienceScreen.currentlyWorkHere')}
              </Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>{t('experienceScreen.description')}</Text>
            <TextInput
              style={[styles.textArea, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={description}
              onChangeText={setDescription}
              placeholder={t('experienceScreen.descriptionPlaceholder')}
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={6}
              textAlignVertical="top"
            />
            <Text style={[styles.helpText, { color: theme.textSecondary }]}>
              {t('experienceScreen.descriptionHelp')}
            </Text>
          </View>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.saveButton, { backgroundColor: theme.primary }]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={20} color="#FFFFFF" />
                <Text style={styles.saveButtonText}>{t('experienceScreen.updateButton')}</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.cancelButton, { borderColor: theme.border }]}
            onPress={() => router.back()}
            disabled={saving}
          >
            <Text style={[styles.cancelButtonText, { color: theme.textSecondary }]}>{t('common.cancel')}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Date Pickers */}
      {showStartPicker && (
        <DateTimePicker
          value={startDate}
          mode="date"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(event: any, selectedDate?: Date) => {
            setShowStartPicker(false);
            if (selectedDate) {
              setStartDate(selectedDate);
              // If start date is after end date, update end date
              if (selectedDate > endDate) {
                setEndDate(selectedDate);
              }
            }
          }}
          maximumDate={new Date()}
        />
      )}

      {showEndPicker && (
        <DateTimePicker
          value={endDate}
          mode="date"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(event: any, selectedDate?: Date) => {
            setShowEndPicker(false);
            if (selectedDate) {
              setEndDate(selectedDate);
            }
          }}
          minimumDate={startDate}
          maximumDate={new Date()}
        />
      )}
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
    fontFamily: 'Poppins_400Regular',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  section: {
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    marginBottom: 20,
  },
  formGroup: {
    marginBottom: 20,
  },
  formRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  formGroupHalf: {
    flex: 1,
  },
  label: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 8,
  },
  required: {
    color: '#EF4444',
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  textArea: {
    minHeight: 120,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  dateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    height: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
  },
  dateButtonText: {
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkboxLabel: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  helpText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    marginTop: 4,
  },
  actions: {
    gap: 12,
    marginBottom: 40,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 56,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  cancelButton: {
    height: 56,
    borderRadius: 16,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
});
