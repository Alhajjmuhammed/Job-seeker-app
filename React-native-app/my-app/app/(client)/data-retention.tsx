import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface RetentionPolicy {
  data_type: string;
  retention_period: string;
  reason: string;
  deletion_method: string;
}

export default function DataRetentionScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [policies, setPolicies] = useState<RetentionPolicy[]>([]);

  useEffect(() => {
    loadRetentionPolicy();
  }, []);

  const loadRetentionPolicy = async () => {
    try {
      const data = await apiService.getDataRetentionPolicy();
      
      // Format the retention policies
      const formattedPolicies: RetentionPolicy[] = [
        {
          data_type: 'Profile Information',
          retention_period: t('dataRetention.profilePeriod'),
          reason: t('dataRetention.profileReason'),
          deletion_method: t('dataRetention.profileMethod'),
        },
        {
          data_type: 'Job History',
          retention_period: t('dataRetention.jobsPeriod'),
          reason: t('dataRetention.jobsReason'),
          deletion_method: t('dataRetention.anonymization'),
        },
        {
          data_type: 'Payment Records',
          retention_period: t('dataRetention.sevenYears'),
          reason: t('dataRetention.paymentsReason'),
          deletion_method: t('dataRetention.paymentsMethod'),
        },
        {
          data_type: 'Messages',
          retention_period: t('dataRetention.messagesPeriod'),
          reason: t('dataRetention.messagesReason'),
          deletion_method: t('dataRetention.permanentDeletion'),
        },
        {
          data_type: 'Reviews & Ratings',
          retention_period: t('dataRetention.reviewsPeriod'),
          reason: t('dataRetention.reviewsReason'),
          deletion_method: t('dataRetention.reviewsMethod'),
        },
        {
          data_type: 'Login History',
          retention_period: t('dataRetention.ninetyDays'),
          reason: t('dataRetention.loginsReason'),
          deletion_method: t('dataRetention.automaticDeletion'),
        },
        {
          data_type: 'Analytics Data',
          retention_period: t('dataRetention.twentyFourMonths'),
          reason: t('dataRetention.analyticsReason'),
          deletion_method: t('dataRetention.automaticDeletion'),
        },
      ];
      
      setPolicies(formattedPolicies);
    } catch (error) {
      console.error('Error loading retention policy:', error);
    } finally {
      setLoading(false);
    }
  };

  // data_type is kept in English (the icon lookup below matches on it); this maps it to its label
  const DATA_TYPE_LABEL: Record<string, string> = {
    'Profile Information': 'dataRetention.types.profile',
    'Job History': 'dataRetention.types.jobs',
    'Payment Records': 'dataRetention.types.payments',
    'Messages': 'dataRetention.types.messages',
    'Reviews & Ratings': 'dataRetention.types.reviews',
    'Login History': 'dataRetention.types.logins',
    'Analytics Data': 'dataRetention.types.analytics',
  };

  const getIconForDataType = (dataType: string) => {
    if (dataType.includes('Profile')) return 'person-outline';
    if (dataType.includes('Job')) return 'briefcase-outline';
    if (dataType.includes('Payment')) return 'card-outline';
    if (dataType.includes('Messages')) return 'chatbubbles-outline';
    if (dataType.includes('Reviews')) return 'star-outline';
    if (dataType.includes('Login')) return 'log-in-outline';
    if (dataType.includes('Analytics')) return 'analytics-outline';
    return 'document-outline';
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title={t('privacy.dataRetentionPolicy')} />
      
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Ionicons name="information-circle" size={32} color={theme.primary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            {t('dataRetention.intro')}
          </Text>
        </View>

        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          {t('dataRetention.periodsByType')}
        </Text>

        {policies.map((policy, index) => (
          <View
            key={index}
            style={[styles.policyCard, { backgroundColor: theme.card }]}
          >
            <View style={styles.policyHeader}>
              <View style={[styles.iconContainer, { backgroundColor: `${theme.primary}15` }]}>
                <Ionicons
                  name={getIconForDataType(policy.data_type) as any}
                  size={24}
                  color={theme.primary}
                />
              </View>
              <Text style={[styles.dataType, { color: theme.text }]}>
                {DATA_TYPE_LABEL[policy.data_type] ? t(DATA_TYPE_LABEL[policy.data_type]) : policy.data_type}
              </Text>
            </View>

            <View style={styles.policyDetail}>
              <View style={styles.detailRow}>
                <Ionicons name="time-outline" size={18} color={theme.textSecondary} />
                <View style={styles.detailText}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    {t('dataRetention.retentionPeriod')}
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.text }]}>
                    {policy.retention_period}
                  </Text>
                </View>
              </View>

              <View style={styles.detailRow}>
                <Ionicons name="help-circle-outline" size={18} color={theme.textSecondary} />
                <View style={styles.detailText}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    {t('dataRetention.reason')}
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.text }]}>
                    {policy.reason}
                  </Text>
                </View>
              </View>

              <View style={styles.detailRow}>
                <Ionicons name="trash-outline" size={18} color={theme.textSecondary} />
                <View style={styles.detailText}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    {t('dataRetention.deletionMethod')}
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.text }]}>
                    {policy.deletion_method}
                  </Text>
                </View>
              </View>
            </View>
          </View>
        ))}

        <View style={[styles.contactCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.contactTitle, { color: theme.text }]}>
            {t('dataRetention.questions')}
          </Text>
          <Text style={[styles.contactText, { color: theme.textSecondary }]}>
            {t('dataRetention.contactDpo')}
          </Text>
          <Text style={[styles.contactEmail, { color: theme.primary }]}>
            privacy@workerconnect.com
          </Text>
        </View>

        <View style={[styles.legalCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.legalTitle, { color: theme.text }]}>
            {t('dataRetention.legalBasis')}
          </Text>
          <Text style={[styles.legalText, { color: theme.textSecondary }]}>
            {t('dataRetention.legalBasisText')}
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
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  infoCard: {
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
    gap: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 16,
  },
  policyCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  policyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  dataType: {
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    flex: 1,
  },
  policyDetail: {
    gap: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  detailText: {
    flex: 1,
  },
  detailLabel: {
    fontSize: 12,
    marginBottom: 2,
  },
  detailValue: {
    fontSize: 14,
    lineHeight: 20,
  },
  contactCard: {
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
    marginBottom: 16,
  },
  contactTitle: {
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 8,
  },
  contactText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 8,
  },
  contactEmail: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  legalCard: {
    padding: 16,
    borderRadius: 12,
  },
  legalTitle: {
    fontSize: 14,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 8,
  },
  legalText: {
    fontSize: 13,
    lineHeight: 18,
  },
});
