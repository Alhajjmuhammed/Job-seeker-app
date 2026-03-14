import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface ConsentSettings {
  marketing_emails: boolean;
  analytics: boolean;
  personalization: boolean;
  third_party_sharing: boolean;
}

export default function PrivacySettingsScreen() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [consents, setConsents] = useState<ConsentSettings>({
    marketing_emails: false,
    analytics: true,
    personalization: true,
    third_party_sharing: false,
  });

  useEffect(() => {
    loadConsentSettings();
  }, []);

  const loadConsentSettings = async () => {
    try {
      const data = await apiService.getConsentStatus();
      if (data.consents) {
        setConsents(data.consents);
      }
    } catch (error) {
      console.error('Error loading consent settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateConsent = async (key: keyof ConsentSettings, value: boolean) => {
    try {
      setSaving(true);
      const newConsents = { ...consents, [key]: value };
      setConsents(newConsents);
      
      await apiService.updateConsentSettings({ [key]: value });
      
      Alert.alert('Success', 'Privacy setting updated');
    } catch (error) {
      console.error('Error updating consent:', error);
      // Revert on error
      setConsents(consents);
      Alert.alert('Error', 'Failed to update privacy setting');
    } finally {
      setSaving(false);
    }
  };

  const handleDataRetention = () => {
    router.push('/(client)/data-retention' as any);
  };

  const handleExportData = async () => {
    try {
      Alert.alert(
        'Export Data',
        'Your data will be prepared and sent to your email address.',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Export',
            onPress: async () => {
              try {
                await apiService.exportMyData();
                Alert.alert(
                  'Export Started',
                  'Your data export has been initiated. You will receive an email shortly.'
                );
              } catch (error) {
                Alert.alert('Error', 'Failed to export data');
              }
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error:', error);
    }
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
      <Header title="Privacy Settings" />
      
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Ionicons name="shield-checkmark" size={32} color={theme.primary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            Control how your data is used and shared. Changes take effect immediately.
          </Text>
        </View>

        {/* Data Consent Settings */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Data Usage Consent</Text>
        
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={[styles.settingTitle, { color: theme.text }]}>
                Marketing Emails
              </Text>
              <Text style={[styles.settingDescription, { color: theme.textSecondary }]}>
                Receive promotional emails and special offers
              </Text>
            </View>
            <Switch
              value={consents.marketing_emails}
              onValueChange={(value) => updateConsent('marketing_emails', value)}
              disabled={saving}
              trackColor={{ false: theme.border, true: theme.primary }}
              thumbColor="#FFFFFF"
            />
          </View>

          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={[styles.settingTitle, { color: theme.text }]}>
                Analytics
              </Text>
              <Text style={[styles.settingDescription, { color: theme.textSecondary }]}>
                Help us improve by sharing anonymous usage data
              </Text>
            </View>
            <Switch
              value={consents.analytics}
              onValueChange={(value) => updateConsent('analytics', value)}
              disabled={saving}
              trackColor={{ false: theme.border, true: theme.primary }}
              thumbColor="#FFFFFF"
            />
          </View>

          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={[styles.settingTitle, { color: theme.text }]}>
                Personalization
              </Text>
              <Text style={[styles.settingDescription, { color: theme.textSecondary }]}>
                Customize your experience based on your activity
              </Text>
            </View>
            <Switch
              value={consents.personalization}
              onValueChange={(value) => updateConsent('personalization', value)}
              disabled={saving}
              trackColor={{ false: theme.border, true: theme.primary }}
              thumbColor="#FFFFFF"
            />
          </View>

          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={[styles.settingTitle, { color: theme.text }]}>
                Third-Party Sharing
              </Text>
              <Text style={[styles.settingDescription, { color: theme.textSecondary }]}>
                Share data with partner services (payment, verification)
              </Text>
            </View>
            <Switch
              value={consents.third_party_sharing}
              onValueChange={(value) => updateConsent('third_party_sharing', value)}
              disabled={saving}
              trackColor={{ false: theme.border, true: theme.primary }}
              thumbColor="#FFFFFF"
            />
          </View>
        </View>

        {/* Data Management */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Data Management</Text>
        
        <View style={[styles.card, { backgroundColor: theme.card }]}>
          <TouchableOpacity
            style={styles.menuItem}
            onPress={handleDataRetention}
          >
            <View style={styles.menuLeft}>
              <Ionicons name="time-outline" size={24} color={theme.primary} />
              <View style={styles.menuText}>
                <Text style={[styles.menuTitle, { color: theme.text }]}>
                  Data Retention Policy
                </Text>
                <Text style={[styles.menuDescription, { color: theme.textSecondary }]}>
                  View how long we keep your data
                </Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          <TouchableOpacity
            style={styles.menuItem}
            onPress={handleExportData}
          >
            <View style={styles.menuLeft}>
              <Ionicons name="download-outline" size={24} color={theme.primary} />
              <View style={styles.menuText}>
                <Text style={[styles.menuTitle, { color: theme.text }]}>
                  Export My Data
                </Text>
                <Text style={[styles.menuDescription, { color: theme.textSecondary }]}>
                  Download a copy of your personal data
                </Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => router.push('/(client)/settings' as any)}
          >
            <View style={styles.menuLeft}>
              <Ionicons name="trash-outline" size={24} color="#EF4444" />
              <View style={styles.menuText}>
                <Text style={[styles.menuTitle, { color: '#EF4444' }]}>
                  Delete Account
                </Text>
                <Text style={[styles.menuDescription, { color: theme.textSecondary }]}>
                  Permanently remove your account
                </Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* GDPR Rights Info */}
        <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
          <Text style={[styles.infoTitle, { color: theme.text }]}>Your GDPR Rights</Text>
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            • Right to Access - View your personal data{'\n'}
            • Right to Rectification - Correct inaccurate data{'\n'}
            • Right to Erasure - Delete your data{'\n'}
            • Right to Data Portability - Export your data{'\n'}
            • Right to Object - Opt out of processing
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
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  card: {
    borderRadius: 12,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 14,
    lineHeight: 18,
  },
  divider: {
    height: 1,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  menuLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  menuText: {
    marginLeft: 12,
    flex: 1,
  },
  menuTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  menuDescription: {
    fontSize: 13,
    lineHeight: 18,
  },
});
