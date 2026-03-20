import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Platform,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { SUPPORTED_LANGUAGES, changeLanguage } from '../../services/i18n';

interface NotificationSettings {
  pushEnabled: boolean;
  emailEnabled: boolean;
  smsEnabled: boolean;
  jobAlerts: boolean;
  messageAlerts: boolean;
  applicationUpdates: boolean;
  marketingEmails: boolean;
}

interface PrivacySettings {
  profileVisible: boolean;
  showLocation: boolean;
  showPhoneNumber: boolean;
  allowDirectMessages: boolean;
}

export default function SettingsScreen() {
  const { t, i18n } = useTranslation();
  const { theme, isDark } = useTheme();
  const { user, logout } = useAuth();
  
  const [loading, setLoading] = useState(false);
  const [showLanguageModal, setShowLanguageModal] = useState(false);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    pushEnabled: true,
    emailEnabled: true,
    smsEnabled: false,
    jobAlerts: true,
    messageAlerts: true,
    applicationUpdates: true,
    marketingEmails: false,
  });

  const [privacySettings, setPrivacySettings] = useState<PrivacySettings>({
    profileVisible: true,
    showLocation: true,
    showPhoneNumber: false,
    allowDirectMessages: true,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [notifSettings, privSettings] = await Promise.all([
        AsyncStorage.getItem('notificationSettings'),
        AsyncStorage.getItem('privacySettings'),
      ]);

      if (notifSettings) {
        setNotificationSettings(JSON.parse(notifSettings));
      }
      if (privSettings) {
        setPrivacySettings(JSON.parse(privSettings));
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveNotificationSettings = async (newSettings: NotificationSettings) => {
    try {
      await AsyncStorage.setItem('notificationSettings', JSON.stringify(newSettings));
      setNotificationSettings(newSettings);
    } catch (error) {
      console.error('Error saving notification settings:', error);
      Alert.alert(t('common.error'), t('nav.settings'));
    }
  };

  const savePrivacySettings = async (newSettings: PrivacySettings) => {
    try {
      await AsyncStorage.setItem('privacySettings', JSON.stringify(newSettings));
      setPrivacySettings(newSettings);
    } catch (error) {
      console.error('Error saving privacy settings:', error);
      Alert.alert(t('common.error'), t('nav.settings'));
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  const handleDeleteAccount = async () => {
    try {
      setLoading(true);
      // First, get preview of what will be deleted
      const preview = await apiService.getAccountDeletionPreview();
      
      Alert.alert(
        'Delete Account',
        `This will permanently delete:\n\n` +
        `• Your profile and personal information\n` +
        `• ${preview.jobs_applied || 0} job applications\n` +
        `• ${preview.jobs_completed || 0} completed jobs\n` +
        `• ${preview.reviews || 0} reviews\n` +
        `• ${preview.messages || 0} messages\n` +
        `• ${preview.earnings || 0} earnings records\n` +
        `• All other associated data\n\n` +
        `⚠️ THIS ACTION CANNOT BE UNDONE!`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Delete Permanently',
            style: 'destructive',
            onPress: confirmDeleteAccount,
          },
        ]
      );
    } catch (error: any) {
      console.error('Error getting deletion preview:', error);
      Alert.alert(
        'Error',
        'Failed to load account information. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const confirmDeleteAccount = () => {
    Alert.alert(
      'Final Confirmation',
      'Are you absolutely sure? This will permanently delete your account and all data.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'I Understand - Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await apiService.deleteAccount();
              Alert.alert(
                'Account Deleted',
                'Your account has been permanently deleted.',
                [
                  {
                    text: 'OK',
                    onPress: async () => {
                      await logout();
                      router.replace('/(auth)/login');
                    },
                  },
                ]
              );
            } catch (error: any) {
              console.error('Error deleting account:', error);
              Alert.alert(
                'Deletion Error',
                error.response?.data?.error || 'Failed to delete account. Please contact support.'
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
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
              setLoading(true);
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
                error.response?.data?.error || 'Failed to start data export. Please try again.'
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const handleLanguageChange = () => {
    setShowLanguageModal(true);
  };

  const handleSelectLanguage = async (code: string) => {
    setShowLanguageModal(false);
    await changeLanguage(code);
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title={t('settings.title')} />

      {/* Language Selection Modal */}
      <Modal
        visible={showLanguageModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowLanguageModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContainer, { backgroundColor: theme.surface }]}>
            <Text style={[styles.modalTitle, { color: theme.text }]}>{t('settings.languageSelect')}</Text>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <TouchableOpacity
                key={lang.code}
                style={[
                  styles.langOption,
                  { borderColor: theme.border },
                  i18n.language === lang.code && { borderColor: theme.primary, backgroundColor: theme.primary + '15' },
                ]}
                onPress={() => handleSelectLanguage(lang.code)}
              >
                <Text style={styles.langFlag}>{lang.flag}</Text>
                <View style={styles.langInfo}>
                  <Text style={[styles.langName, { color: theme.text }]}>{lang.name}</Text>
                  <Text style={[styles.langNative, { color: theme.textSecondary }]}>{lang.nativeName}</Text>
                </View>
                {i18n.language === lang.code && (
                  <Ionicons name="checkmark-circle" size={22} color={theme.primary} />
                )}
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              style={[styles.modalCancel, { borderColor: theme.border }]}
              onPress={() => setShowLanguageModal(false)}
            >
              <Text style={[styles.modalCancelText, { color: theme.textSecondary }]}>{t('common.cancel')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Account Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('settings.account')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleLanguageChange}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="language-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.language')}</Text>
              </View>
              <View style={styles.settingRight}>
                <Text style={[styles.settingValue, { color: theme.textSecondary }]}>
                  {SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language)?.flag}{' '}
                  {SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language)?.name ?? 'English'}
                </Text>
                <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
              </View>
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.settingRow}
              onPress={() => router.push('/(worker)/payout-methods')}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="card-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('paymentMethods.paymentMethodsTitle')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Security Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('clientSettings.security')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={() => router.push('/(worker)/change-password')}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="lock-closed-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('security.changePassword')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Notification Settings */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('settings.notifications')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="notifications-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.pushNotifications')}</Text>
              </View>
              <Switch
                value={notificationSettings.pushEnabled}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, pushEnabled: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.pushEnabled ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="mail-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.emailNotifications')}</Text>
              </View>
              <Switch
                value={notificationSettings.emailEnabled}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, emailEnabled: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.emailEnabled ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="chatbox-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.smsNotifications')}</Text>
              </View>
              <Switch
                value={notificationSettings.smsEnabled}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, smsEnabled: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.smsEnabled ? '#0F766E' : '#9CA3AF'}
              />
            </View>
          </View>

          {/* Notification Preferences */}
          <View style={[styles.card, { backgroundColor: theme.surface, marginTop: 12 }]}>
            <View style={styles.settingRow}>
              <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.jobAlerts')}</Text>
              <Switch
                value={notificationSettings.jobAlerts}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, jobAlerts: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.jobAlerts ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.messageAlerts')}</Text>
              <Switch
                value={notificationSettings.messageAlerts}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, messageAlerts: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.messageAlerts ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.applicationUpdates')}</Text>
              <Switch
                value={notificationSettings.applicationUpdates}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, applicationUpdates: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.applicationUpdates ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.marketingEmails')}</Text>
              <Switch
                value={notificationSettings.marketingEmails}
                onValueChange={(value) =>
                  saveNotificationSettings({ ...notificationSettings, marketingEmails: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={notificationSettings.marketingEmails ? '#0F766E' : '#9CA3AF'}
              />
            </View>
          </View>
        </View>

        {/* Privacy Settings */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('settings.privacy')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="eye-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.profileVisible')}</Text>
              </View>
              <Switch
                value={privacySettings.profileVisible}
                onValueChange={(value) =>
                  savePrivacySettings({ ...privacySettings, profileVisible: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={privacySettings.profileVisible ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="location-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.showLocation')}</Text>
              </View>
              <Switch
                value={privacySettings.showLocation}
                onValueChange={(value) =>
                  savePrivacySettings({ ...privacySettings, showLocation: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={privacySettings.showLocation ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="call-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.showPhoneNumber')}</Text>
              </View>
              <Switch
                value={privacySettings.showPhoneNumber}
                onValueChange={(value) =>
                  savePrivacySettings({ ...privacySettings, showPhoneNumber: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={privacySettings.showPhoneNumber ? '#0F766E' : '#9CA3AF'}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="chatbubbles-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('settings.allowMessages')}</Text>
              </View>
              <Switch
                value={privacySettings.allowDirectMessages}
                onValueChange={(value) =>
                  savePrivacySettings({ ...privacySettings, allowDirectMessages: value })
                }
                trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
                thumbColor={privacySettings.allowDirectMessages ? '#0F766E' : '#9CA3AF'}
              />
            </View>
          </View>
        </View>

        {/* GDPR & Data Rights */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('clientSettings.privacyDataGDPR')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={() => router.push('/(worker)/privacy-settings')}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="shield-checkmark-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('privacy.privacySettings')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.settingRow}
              onPress={() => router.push('/(worker)/data-retention')}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="time-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('clientSettings.dataRetentionInfo')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleExportData}
              disabled={loading}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="download-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>{t('clientSettings.exportDataTitle')}</Text>
              </View>
              {loading ? (
                <ActivityIndicator size="small" color={theme.primary} />
              ) : (
                <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
              )}
            </TouchableOpacity>
          </View>
        </View>

        {/* Danger Zone */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: '#EF4444' }]}>{t('clientSettings.dangerZone')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleLogout}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="log-out-outline" size={24} color="#F59E0B" />
                <Text style={[styles.settingText, { color: '#F59E0B' }]}>{t('nav.logout')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleDeleteAccount}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="trash-outline" size={24} color="#EF4444" />
                <Text style={[styles.settingText, { color: '#EF4444' }]}>{t('clientSettings.deleteAccountTitle')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* App Info */}
        <View style={styles.appInfo}>
          <Text style={[styles.appInfoText, { color: theme.textSecondary }]}>
            WorkerConnect v1.0.0
          </Text>
          <Text style={[styles.appInfoText, { color: theme.textSecondary }]}>
            © 2026 WorkerConnect. All rights reserved.
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
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  card: {
    borderRadius: 16,
    padding: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  settingRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  settingText: {
    fontSize: 15,
    fontFamily: 'Poppins_500Medium',
  },
  settingValue: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  divider: {
    height: 1,
    marginHorizontal: 16,
  },
  appInfo: {
    alignItems: 'center',
    marginTop: 24,
    gap: 4,
  },
  appInfoText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 36,
  },
  modalTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  langOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    marginBottom: 10,
  },
  langFlag: {
    fontSize: 26,
  },
  langInfo: {
    flex: 1,
  },
  langName: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
  },
  langNative: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  modalCancel: {
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    alignItems: 'center',
    marginTop: 4,
  },
  modalCancelText: {
    fontSize: 15,
    fontFamily: 'Poppins_500Medium',
  },
});
