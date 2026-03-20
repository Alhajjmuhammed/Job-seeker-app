import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface PrivacySettings {
  email_notifications: boolean;
  sms_notifications: boolean;
  push_notifications: boolean;
  marketing_emails: boolean;
  profile_visibility: 'public' | 'private' | 'connections_only';
  show_email: boolean;
  show_phone: boolean;
  allow_search_indexing: boolean;
}

export default function PrivacySettingsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<PrivacySettings>({
    email_notifications: true,
    sms_notifications: false,
    push_notifications: true,
    marketing_emails: false,
    profile_visibility: 'public',
    show_email: false,
    show_phone: false,
    allow_search_indexing: true,
  });

  useEffect(() => {
    loadPrivacySettings();
  }, []);

  const loadPrivacySettings = async () => {
    try {
      setLoading(true);
      const response = await apiService.getPrivacySettings();
      setSettings(response);
    } catch (error: any) {
      console.error('Error loading privacy settings:', error);
      Alert.alert(
        'Error',
        'Failed to load privacy settings. Using default values.'
      );
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key: keyof PrivacySettings, value: any) => {
    try {
      setSaving(true);
      const updatedSettings = { ...settings, [key]: value };
      setSettings(updatedSettings);
      
      await apiService.updatePrivacySettings({ [key]: value });
      
      Alert.alert(t('common.success'), t('privacy.privacySettingUpdated'));
    } catch (error: any) {
      console.error('Error updating privacy setting:', error);
      Alert.alert(
        'Error',
        error.response?.data?.error || 'Failed to update privacy setting'
      );
      // Revert the change
      loadPrivacySettings();
    } finally {
      setSaving(false);
    }
  };

  const handleDataRetention = () => {
    router.push('/(client)/data-retention');
  };

  const handleExportData = () => {
    Alert.alert(
      'Export My Data',
      'We will prepare a complete export of all your data and email it to you. This may take a few minutes.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Export',
          onPress: async () => {
            try {
              await apiService.exportUserData();
              Alert.alert(
                'Export Started',
                'Your data export has been started. You will receive an email with a download link shortly.',
                [{ text: 'OK' }]
              );
            } catch (error: any) {
              console.error('Error exporting data:', error);
              Alert.alert(
                'Export Error',
                error.response?.data?.error || 'Failed to start data export'
              );
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header title="Privacy Settings" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>{t('privacy.loadingPrivacySettings')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Privacy Settings" showBack />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Communication Preferences */}
        <Text
          style={[
            styles.sectionTitle,
            { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
          ]}
        >{t('privacy.communication')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={[styles.settingItem, { borderBottomColor: theme.border }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.emailNotifications')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.receiveEmailNotifications')}</Text>
            </View>
            <Switch
              value={settings.email_notifications}
              onValueChange={(value) => updateSetting('email_notifications', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>

          <View style={[styles.settingItem, { borderBottomColor: theme.border }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.smsNotifications')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.receiveSMSNotifications')}</Text>
            </View>
            <Switch
              value={settings.sms_notifications}
              onValueChange={(value) => updateSetting('sms_notifications', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>

          <View style={[styles.settingItem, { borderBottomColor: theme.border }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.pushNotifications')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.receivePushNotifications')}</Text>
            </View>
            <Switch
              value={settings.push_notifications}
              onValueChange={(value) => updateSetting('push_notifications', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>

          <View style={[styles.settingItem, { borderBottomColor: 'transparent' }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.marketingEmails')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >
                Receive promotional emails and newsletters
              </Text>
            </View>
            <Switch
              value={settings.marketing_emails}
              onValueChange={(value) => updateSetting('marketing_emails', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>
        </View>

        {/* Profile Visibility */}
        <Text
          style={[
            styles.sectionTitle,
            { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
          ]}
        >{t('privacy.profileVisibility')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={[styles.settingItem, { borderBottomColor: theme.border }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.showEmailAddress')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.displayEmail')}</Text>
            </View>
            <Switch
              value={settings.show_email}
              onValueChange={(value) => updateSetting('show_email', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>

          <View style={[styles.settingItem, { borderBottomColor: theme.border }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.showPhoneNumber')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.displayPhone')}</Text>
            </View>
            <Switch
              value={settings.show_phone}
              onValueChange={(value) => updateSetting('show_phone', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>

          <View style={[styles.settingItem, { borderBottomColor: 'transparent' }]}>
            <View style={styles.settingInfo}>
              <Text
                style={[
                  styles.settingLabel,
                  { color: theme.text, fontFamily: 'Poppins_500Medium' },
                ]}
              >{t('privacy.searchEngineIndexing')}</Text>
              <Text
                style={[
                  styles.settingDescription,
                  { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
                ]}
              >{t('privacy.allowSearchEngines')}</Text>
            </View>
            <Switch
              value={settings.allow_search_indexing}
              onValueChange={(value) => updateSetting('allow_search_indexing', value)}
              trackColor={{ false: theme.border, true: theme.primary }}
              disabled={saving}
            />
          </View>
        </View>

        {/* Data Management */}
        <Text
          style={[
            styles.sectionTitle,
            { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' },
          ]}
        >{t('privacy.dataManagement')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={handleDataRetention}
          >
            <Ionicons
              name="time-outline"
              size={22}
              color={theme.primary}
              style={styles.menuIcon}
            />
            <Text
              style={[
                styles.menuText,
                { color: theme.text, fontFamily: 'Poppins_500Medium' },
              ]}
            >{t('privacy.dataRetentionPolicy')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={handleExportData}
          >
            <Ionicons
              name="download-outline"
              size={22}
              color={theme.primary}
              style={styles.menuIcon}
            />
            <Text
              style={[
                styles.menuText,
                { color: theme.text, fontFamily: 'Poppins_500Medium' },
              ]}
            >{t('clientSettings.exportDataTitle')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* Information */}
        <View style={styles.infoBox}>
          <Ionicons name="information-circle" size={20} color={theme.primary} />
          <Text
            style={[
              styles.infoText,
              { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' },
            ]}
          >
            Your privacy is important to us. These settings help you control how your
            data is used and who can see your information. Learn more in our{' '}
            <Text style={{ color: theme.primary }}>{t('auth.privacyPolicy')}</Text>.
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
    paddingBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 24,
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  section: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
  },
  settingInfo: {
    flex: 1,
    marginRight: 12,
  },
  settingLabel: {
    fontSize: 16,
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 13,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  menuIcon: {
    marginRight: 12,
  },
  menuText: {
    flex: 1,
    fontSize: 16,
  },
  infoBox: {
    flexDirection: 'row',
    marginTop: 20,
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
  },
  infoText: {
    flex: 1,
    marginLeft: 12,
    fontSize: 13,
    lineHeight: 18,
  },
});
