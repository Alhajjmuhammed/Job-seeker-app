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
          retention_period: 'Active account + 30 days after deletion',
          reason: 'Service delivery and account recovery',
          deletion_method: 'Permanent deletion or anonymization',
        },
        {
          data_type: 'Job History',
          retention_period: 'Active account + 7 years',
          reason: 'Legal compliance and dispute resolution',
          deletion_method: 'Anonymization',
        },
        {
          data_type: 'Payment Records',
          retention_period: '7 years',
          reason: 'Tax and financial compliance',
          deletion_method: 'Secure archival then deletion',
        },
        {
          data_type: 'Messages',
          retention_period: 'Active account + 90 days',
          reason: 'Service continuity and quality',
          deletion_method: 'Permanent deletion',
        },
        {
          data_type: 'Reviews & Ratings',
          retention_period: 'Permanent (anonymized)',
          reason: 'Platform integrity and trust',
          deletion_method: 'Name/email removed, content preserved',
        },
        {
          data_type: 'Login History',
          retention_period: '90 days',
          reason: 'Security and fraud prevention',
          deletion_method: 'Automatic deletion',
        },
        {
          data_type: 'Analytics Data',
          retention_period: '24 months',
          reason: 'Service improvement',
          deletion_method: 'Automatic deletion',
        },
      ];
      
      setPolicies(formattedPolicies);
    } catch (error) {
      console.error('Error loading retention policy:', error);
    } finally {
      setLoading(false);
    }
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
      <Header title="Data Retention Policy" />
      
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Ionicons name="information-circle" size={32} color={theme.primary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            We retain your data only as long as necessary to provide our services and comply with legal obligations.
          </Text>
        </View>

        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          Retention Periods by Data Type
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
                {policy.data_type}
              </Text>
            </View>

            <View style={styles.policyDetail}>
              <View style={styles.detailRow}>
                <Ionicons name="time-outline" size={18} color={theme.textSecondary} />
                <View style={styles.detailText}>
                  <Text style={[styles.detailLabel, { color: theme.textSecondary }]}>
                    Retention Period
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
                    Reason
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
                    Deletion Method
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
            Questions or Concerns?
          </Text>
          <Text style={[styles.contactText, { color: theme.textSecondary }]}>
            If you have any questions about how we handle your data, please contact our Data Protection Officer:
          </Text>
          <Text style={[styles.contactEmail, { color: theme.primary }]}>
            privacy@workerconnect.com
          </Text>
        </View>

        <View style={[styles.legalCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.legalTitle, { color: theme.text }]}>
            Legal Basis
          </Text>
          <Text style={[styles.legalText, { color: theme.textSecondary }]}>
            We process your data under GDPR Article 6(1)(b) for contract performance and Article 6(1)(c) for legal compliance. Some processing is based on your consent (Article 6(1)(a)).
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
    fontWeight: 'bold',
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
    fontWeight: 'bold',
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
    fontWeight: 'bold',
    marginBottom: 8,
  },
  contactText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 8,
  },
  contactEmail: {
    fontSize: 14,
    fontWeight: '600',
  },
  legalCard: {
    padding: 16,
    borderRadius: 12,
  },
  legalTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  legalText: {
    fontSize: 13,
    lineHeight: 18,
  },
});
