import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import apiService from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import { useTranslation } from 'react-i18next';

interface CurrentAssignment {
  id: number;
  title: string;
  description: string;
  category_name: string;
  urgency: 'normal' | 'urgent' | 'emergency';
  status: string;
  location: string;
  city: string;
  estimated_duration_hours: number;
  client_name: string;
  client_phone: string;
  work_started_at: string | null;
}

export default function ActiveService() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [assignment, setAssignment] = useState<CurrentAssignment | null>(null);

  useEffect(() => {
    loadCurrentAssignment();
  }, []);

  const loadCurrentAssignment = async () => {
    try {
      setLoading(true);
      const response = await apiService.getCurrentAssignment();
      
      if (response.service_request) {
        setAssignment(response.service_request);
      } else {
        Alert.alert(t('assignments.noActiveService'), 'You don\'t have any active service assignment', [
          { text: 'OK', onPress: () => router.back() }
        ]);
      }
    } catch (error: any) {
      console.error('Error loading current assignment:', error);
      if (error.response?.status === 404) {
        Alert.alert(t('assignments.noActiveService'), 'You don\'t have any active service assignment', [
          { text: 'OK', onPress: () => router.back() }
        ]);
      } else {
        Alert.alert(t('common.error'), error.response?.data?.error || 'Failed to load active service');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCallClient = () => {
    if (assignment?.client_phone) {
      Linking.openURL(`tel:${assignment.client_phone}`);
    }
  };

  const getUrgencyConfig = (urgency: string) => {
    const configs = {
      normal: { bg: '#e8f5e9', text: '#2e7d32' },
      urgent: { bg: '#fff3e0', text: '#e65100' },
      emergency: { bg: '#ffebee', text: '#c62828' },
    };
    return configs[urgency as keyof typeof configs] || configs.normal;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Active Service" showBack />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
        <StatusBar style={isDark ? 'light' : 'dark'} />
      </View>
    );
  }

  if (!assignment) {
    return null;
  }

  const urgencyConfig = getUrgencyConfig(assignment.urgency);

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Active Service" showBack />
      
      <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
        {/* Status Card */}
        <View style={[styles.statusCard, { backgroundColor: theme.card }]}>
          <View style={styles.statusHeader}>
            <Ionicons 
              name="briefcase"
              size={32} 
              color={theme.primary}
            />
            <View style={styles.statusContent}>
              <Text style={[styles.statusTitle, { color: theme.text }]}>{t('assignments.activeService')}</Text>
              <Text style={[styles.statusSubtitle, { color: theme.textSecondary }]}>{t('assignments.currentlyWorking')}</Text>
            </View>
          </View>
        </View>

        {/* Service Info */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.title, { color: theme.text }]}>{assignment.title}</Text>
          
          <View style={styles.categoryRow}>
            <Ionicons name="briefcase-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.categoryText, { color: theme.textSecondary }]}>
              {assignment.category_name}
            </Text>
          </View>

          <View style={[styles.urgencyBadge, { backgroundColor: urgencyConfig.bg }]}>
            <Text style={[styles.urgencyText, { color: urgencyConfig.text }]}>
              {assignment.urgency.toUpperCase()} PRIORITY
            </Text>
          </View>

          <Text style={[styles.description, { color: theme.textSecondary }]}>
            {assignment.description}
          </Text>
        </View>

        {/* Client Info */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('assignments.client')}</Text>
          
          <View style={styles.infoRow}>
            <Ionicons name="person-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              {assignment.client_name}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="call-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              {assignment.client_phone}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="location-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              {assignment.city}, {assignment.location}
            </Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="hourglass-outline" size={20} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.text }]}>
              Est. {assignment.estimated_duration_hours} hour{assignment.estimated_duration_hours !== 1 ? 's' : ''}
            </Text>
          </View>
        </View>

        {/* Contact Client Actions */}
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('assignments.clientContact')}</Text>
          
          <Text style={[styles.infoText, { color: theme.textSecondary, marginBottom: 16 }]}>{t('assignments.needReachClient')}</Text>

          <TouchableOpacity
            style={[styles.callButton, { backgroundColor: theme.primary }]}
            onPress={handleCallClient}
          >
            <Ionicons name="call" size={24} color="#fff" />
            <Text style={styles.callButtonText}>{t('assignments.callClient')}</Text>
          </TouchableOpacity>
        </View>

        {/* Important Info */}
        <View style={[styles.infoCard, { backgroundColor: theme.primary + '15' }]}>
          <Ionicons name="information-circle" size={24} color={theme.primary} />
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={[styles.infoCardTitle, { color: theme.primary }]}>{t('assignments.workInProgress')}</Text>
            <Text style={[styles.infoCardText, { color: theme.text }]}>{t('assignments.continueWorking')}</Text>
          </View>
        </View>
      </ScrollView>

      <StatusBar style={isDark ? 'light' : 'dark'} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  statusCard: {
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  statusContent: {
    flex: 1,
  },
  statusTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statusSubtitle: {
    fontSize: 16,
  },
  card: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  categoryText: {
    fontSize: 14,
  },
  urgencyBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  urgencyText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  infoText: {
    fontSize: 15,
    flex: 1,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    minHeight: 80,
    marginBottom: 16,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
  },
  secondaryButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  completeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 12,
  },
  completeButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  disabledButton: {
    opacity: 0.5,
  },
  callButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 10,
  },
  callButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  infoCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
  },
  infoCardTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
  },
  infoCardText: {
    fontSize: 14,
    lineHeight: 20,
  },});