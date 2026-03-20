import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface DataRetentionInfo {
  category: string;
  description: string;
  retention_period: string;
  icon: string;
  data_count?: number;
}

export default function DataRetentionScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [retentionData, setRetentionData] = useState<DataRetentionInfo[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    loadDataRetention();
  }, []);

  const loadDataRetention = async () => {
    try {
      setLoading(true);
      const response = await apiService.getDataRetention();
      setRetentionData(response.retention_policies || []);
      setLastUpdated(response.last_updated || new Date().toISOString());
    } catch (error: any) {
      console.error('Error loading data retention:', error);
      // Show default data if API fails
      setRetentionData(getDefaultRetentionData());
      setLastUpdated(new Date().toISOString());
    } finally {
      setLoading(false);
    }
  };

  const getDefaultRetentionData = (): DataRetentionInfo[] => {
    return [
      {
        category: 'Profile Information',
        description: 'Your name, email, phone number, and profile picture',
        retention_period: 'Until account deletion',
        icon: 'person-circle-outline',
      },
      {
        category: 'Service Requests',
        description: 'Service requests you\'ve created, including descriptions and status',
        retention_period: '3 years after completion',
        icon: 'document-text-outline',
      },
      {
        category: 'Messages & Chat',
        description: 'Messages exchanged with service providers',
        retention_period: '2 years after last message',
        icon: 'chatbubbles-outline',
      },
      {
        category: 'Payment Information',
        description: 'Transaction history and payment methods',
        retention_period: '7 years (legal requirement)',
        icon: 'card-outline',
      },
      {
        category: 'Reviews & Ratings',
        description: 'Reviews you\'ve written and ratings you\'ve given',
        retention_period: 'Permanently (anonymized after 5 years)',
        icon: 'star-outline',
      },
      {
        category: 'Location Data',
        description: 'Service locations and addresses you\'ve saved',
        retention_period: '1 year after last use',
        icon: 'location-outline',
      },
      {
        category: 'Usage Analytics',
        description: 'App usage patterns, device info, and crash reports',
        retention_period: '18 months',
        icon: 'analytics-outline',
      },
      {
        category: 'Notifications',
        description: 'Notification history and preferences',
        retention_period: '90 days after sending',
        icon: 'notifications-outline',
      },
    ];
  };

  const handleExportData = () => {
    Alert.alert(
      'Export My Data',
      'We will prepare a complete export of all your data and email it to you within 24 hours.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Export',
          onPress: async () => {
            try {
              await apiService.exportUserData();
              Alert.alert(
                'Export Started',
                'Your data export request has been received. You will receive an email with a download link shortly.',
                [{ text: 'OK' }]
              );
            } catch (error: any) {
              console.error('Error exporting data:', error);
              Alert.alert(
                'Export Error',
                error.response?.data?.error || 'Failed to start data export. Please try again.'
              );
            }
          },
        },
      ]
    );
  };

  const getIconName = (iconString: string): any => {
    return iconString as any;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header title="Data Retention" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
            Loading data retention information...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Data Retention" showBack />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header Info */}
        <View style={styles.headerInfo}>
          <Ionicons name="time-outline" size={48} color={theme.primary} />
          <Text
            style={[
              styles.headerTitle,
              { color: theme.text, fontFamily: 'Poppins_600SemiBold' },
            ]}
          >
            How Long We Keep Your Data
          </Text>
          <Text
            style={[
              styles.headerDescription,
              { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
            ]}
          >
            We retain your data only as long as necessary to provide our services
            and comply with legal obligations.
          </Text>
        </View>

        {/* Data Categories */}
        {retentionData.map((item, index) => (
          <View
            key={index}
            style={[
              styles.categoryCard,
              { backgroundColor: theme.card, borderColor: theme.border },
            ]}
          >
            <View style={styles.categoryHeader}>
              <View
                style={[
                  styles.iconContainer,
                  { backgroundColor: `${theme.primary}15` },
                ]}
              >
                <Ionicons
                  name={getIconName(item.icon)}
                  size={24}
                  color={theme.primary}
                />
              </View>
              <View style={styles.categoryInfo}>
                <Text
                  style={[
                    styles.categoryTitle,
                    { color: theme.text, fontFamily: 'Poppins_600SemiBold' },
                  ]}
                >
                  {item.category}
                </Text>
                {item.data_count !== undefined && (
                  <Text
                    style={[
                      styles.dataCount,
                      { color: theme.primary, fontFamily: 'Poppins_500Medium' },
                    ]}
                  >
                    {item.data_count} items
                  </Text>
                )}
              </View>
            </View>

            <Text
              style={[
                styles.categoryDescription,
                { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
              ]}
            >
              {item.description}
            </Text>

            <View
              style={[
                styles.retentionPeriod,
                { backgroundColor: theme.background, borderColor: theme.border },
              ]}
            >
              <Ionicons name="calendar-outline" size={16} color={theme.primary} />
              <Text
                style={[
                  styles.retentionText,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >
                Retention: {item.retention_period}
              </Text>
            </View>
          </View>
        ))}

        {/* Actions */}
        <View style={styles.actionsSection}>
          <Text
            style={[
              styles.sectionTitle,
              { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
            ]}
          >
            Data Management Actions
          </Text>

          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: theme.primary }]}
            onPress={handleExportData}
          >
            <Ionicons name="download-outline" size={22} color="#FFFFFF" />
            <Text style={[styles.actionButtonText, { fontFamily: 'Poppins_600SemiBold' }]}>
              Export All My Data
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.actionButtonOutline,
              { borderColor: theme.border, backgroundColor: theme.card },
            ]}
            onPress={() =>
              Alert.alert(
                'Data Deletion',
                'To permanently delete your data, please use the "Delete Account" option in Settings.',
                [{ text: 'OK' }]
              )
            }
          >
            <Ionicons name="trash-outline" size={22} color={theme.textSecondary} />
            <Text
              style={[
                styles.actionButtonOutlineText,
                { color: theme.text, fontFamily: 'Poppins_600SemiBold' },
              ]}
            >
              Request Data Deletion
            </Text>
          </TouchableOpacity>
        </View>

        {/* Legal Info */}
        <View style={styles.legalInfo}>
          <Ionicons
            name="information-circle-outline"
            size={20}
            color={theme.textSecondary}
          />
          <View style={styles.legalTextContainer}>
            <Text
              style={[
                styles.legalText,
                { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
              ]}
            >
              Data retention periods are based on legal requirements and business needs.
              Some data may be retained longer for legal compliance.
            </Text>
            <Text
              style={[
                styles.lastUpdated,
                { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
              ]}
            >
              Last updated: {new Date(lastUpdated).toLocaleDateString()}
            </Text>
          </View>
        </View>

        {/* Contact Support */}
        <TouchableOpacity
          style={styles.supportLink}
          onPress={() =>
            Alert.alert(
              'Contact Support',
              'For questions about data retention, please email privacy@workerconnect.com'
            )
          }
        >
          <Text
            style={[
              styles.supportLinkText,
              { color: theme.primary, fontFamily: 'Poppins_500Medium' },
            ]}
          >{t('nav.support')}</Text>
          <Ionicons name="arrow-forward" size={18} color={theme.primary} />
        </TouchableOpacity>
      </ScrollView>
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
    paddingHorizontal: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingBottom: 32,
  },
  headerInfo: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 22,
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  headerDescription: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
  categoryCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
  },
  categoryHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  categoryInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  categoryTitle: {
    fontSize: 17,
    marginBottom: 4,
  },
  dataCount: {
    fontSize: 13,
  },
  categoryDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  retentionPeriod: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
  },
  retentionText: {
    fontSize: 13,
    marginLeft: 6,
  },
  actionsSection: {
    marginTop: 24,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    marginLeft: 8,
  },
  actionButtonOutline: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  actionButtonOutlineText: {
    fontSize: 16,
    marginLeft: 8,
  },
  legalInfo: {
    flexDirection: 'row',
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(156, 163, 175, 0.1)',
  },
  legalTextContainer: {
    flex: 1,
    marginLeft: 12,
  },
  legalText: {
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 8,
  },
  lastUpdated: {
    fontSize: 11,
    fontStyle: 'italic',
  },
  supportLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    padding: 16,
  },
  supportLinkText: {
    fontSize: 15,
    marginRight: 6,
  },
});
