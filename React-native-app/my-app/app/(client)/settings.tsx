import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import LanguagePicker from '../../components/LanguagePicker';
import { confirmExportMyData } from '../../services/exportMyData';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

export default function ClientSettingsScreen() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [exportingData, setExportingData] = useState(false);

  // Notification preferences - loaded from and persisted to the backend
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [smsNotifications, setSmsNotifications] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const backend = await apiService.getPrivacySettings();
        setEmailNotifications(backend.email_notifications ?? true);
        setPushNotifications(backend.push_notifications ?? true);
        setSmsNotifications(backend.sms_notifications ?? false);
      } catch (error) {
        console.error('Error loading privacy settings:', error);
      }
    })();
  }, []);

  const updateNotificationPref = async (key: 'email_notifications' | 'push_notifications' | 'sms_notifications', value: boolean) => {
    try {
      await apiService.updatePrivacySettings({ [key]: value });
    } catch (error) {
      console.error(`Error updating ${key}:`, error);
      // put the switch back so it shows what is really saved
      const revert = { email_notifications: setEmailNotifications, push_notifications: setPushNotifications,
                       sms_notifications: setSmsNotifications }[key];
      revert(!value);
      Alert.alert(t('common.error'), t('settingsScreen.failedUpdateSetting'));
    }
  };

  const handleExportData = () => confirmExportMyData(setExportingData);

  const handleDeleteAccount = async () => {
    try {
      setLoading(true);
      // First, get preview of what will be deleted
      const preview = await apiService.getAccountDeletionPreview();
      
      // GDPRService.get_erasure_preview() (accounts/gdpr.py) returns
      // jobs_count/messages_count/reviews_given_count/reviews_received_count
      // - not service_requests/reviews/messages. Those never matched, so
      // this confirmation always understated the deletion impact as "0"
      // right before an irreversible action.
      Alert.alert(
        t('clientSettings.deleteAccountTitle'),
        t('settingsScreen.deleteIntro') +
        t('settingsScreen.deleteProfileLine') +
        t('settingsScreen.deleteRequestsLine', { n: preview.jobs_count || 0 }) +
        t('settingsScreen.deleteReviewsLine', { n: (preview.reviews_given_count || 0) + (preview.reviews_received_count || 0) }) +
        t('settingsScreen.deleteMessagesLine', { n: preview.messages_count || 0 }) +
        t('settingsScreen.deleteOtherLine') +
        t('settingsScreen.cannotUndo'),
        [
          { text: t('common.cancel'), style: 'cancel' },
          {
            text: t('clientSettings.deletePermanently'),
            style: 'destructive',
            onPress: confirmDeleteAccount,
          },
        ]
      );
    } catch (error: any) {
      console.error('Error getting deletion preview:', error);
      Alert.alert(
        t('common.error'),
        t('clientSettings.failedLoadAccount')
      );
    } finally {
      setLoading(false);
    }
  };

  const confirmDeleteAccount = () => {
    Alert.alert(
      t('clientSettings.finalConfirmation'),
      t('clientSettings.typeDELETE'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('clientSettings.iUnderstand'),
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await apiService.deleteAccount();
              Alert.alert(
                t('clientSettings.accountDeleted'),
                t('clientSettings.accountDeletedMessage'),
                [
                  {
                    text: t('common.ok'),
                    onPress: async () => {
                      await logout();
                    },
                  },
                ]
              );
            } catch (error: any) {
              console.error('Error deleting account:', error);
              Alert.alert(
                t('clientSettings.deletionError'),
                error.response?.data?.error || t('clientSettings.failedDeleteAccount')
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const handleAnonymizeAccount = () => {
    Alert.alert(
      t('clientSettings.anonymizeAccount'),
      t('clientSettings.anonymizeAccountMessage'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('clientSettings.anonymize'),
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await apiService.anonymizeAccount();
              Alert.alert(
                t('clientSettings.accountAnonymized'),
                t('clientSettings.accountAnonymizedMessage'),
                [
                  {
                    text: t('common.ok'),
                    onPress: async () => {
                      await logout();
                    },
                  },
                ]
              );
            } catch (error: any) {
              console.error('Error anonymizing account:', error);
              Alert.alert(
                t('common.error'),
                error.response?.data?.error || t('clientSettings.failedAnonymize')
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title={t('settings.title')} />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Account Settings */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('client.accountSettings')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <LanguagePicker
            rowStyle={[styles.menuItem, { borderBottomColor: theme.border }]}
            labelStyle={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}
            iconSize={22}
          />

          <TouchableOpacity
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/profile-edit')}
          >
            <Ionicons name="person-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('profile.editProfile')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => router.push('/(client)/payment-methods')}
          >
            <Ionicons name="card-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('paymentMethods.paymentMethodsTitle')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

        </View>

        {/* Security */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.security')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => router.push('/(client)/change-password')}
          >
            <Ionicons name="lock-closed-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('security.changePassword')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* Notifications */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('settings.notifications')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/notifications')}
          >
            <Ionicons name="list-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.notificationHistory')}</Text>
            <Ionicons name="chevron-forward" size={22} color={theme.textSecondary} />
          </TouchableOpacity>

          <View style={[styles.menuItem, { borderBottomColor: theme.border }]}>
            <Ionicons name="mail-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.emailNotifications')}</Text>
            <Switch
              value={emailNotifications}
              onValueChange={(value) => {
                setEmailNotifications(value);
                updateNotificationPref('email_notifications', value);
              }}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>

          <View style={[styles.menuItem, { borderBottomColor: theme.border }]}>
            <Ionicons name="notifications-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.pushNotifications')}</Text>
            <Switch
              value={pushNotifications}
              onValueChange={(value) => {
                setPushNotifications(value);
                updateNotificationPref('push_notifications', value);
              }}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>

          <View style={[styles.menuItem, { borderBottomColor: 'transparent' }]}>
            <Ionicons name="chatbox-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.smsNotifications')}</Text>
            <Switch
              value={smsNotifications}
              onValueChange={(value) => {
                setSmsNotifications(value);
                updateNotificationPref('sms_notifications', value);
              }}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>
        </View>

        {/* Appearance */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.appearance')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={[styles.menuItem, { borderBottomColor: 'transparent' }]}>
            <Ionicons name={isDark ? "moon" : "sunny"} size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.darkMode')}</Text>
            <Switch
              value={isDark}
              onValueChange={toggleTheme}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>
        </View>

        {/* Privacy & Data */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.privacyDataGDPR')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={handleExportData}
            disabled={exportingData}
          >
            <Ionicons name="download-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.exportDataTitle')}</Text>
            {exportingData ? (
              <ActivityIndicator size="small" color={theme.primary} />
            ) : (
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            )}
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/privacy-settings')}
          >
            <Ionicons name="shield-checkmark-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.privacySettings')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/data-retention')}
          >
            <Ionicons name="time-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.dataRetentionInfo')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={handleAnonymizeAccount}
            disabled={loading}
          >
            <Ionicons name="eye-off-outline" size={22} color="#F59E0B" style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: '#F59E0B', fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.anonymizeAccount')}</Text>
            {loading ? (
              <ActivityIndicator size="small" color="#F59E0B" />
            ) : (
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            )}
          </TouchableOpacity>
        </View>

        {/* Support */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.supportSection')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/support')}
          >
            <Ionicons name="help-circle-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.helpCenter')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/support')}
          >
            <Ionicons name="mail-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.contactSupport')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => router.push('/terms' as any)}
          >
            <Ionicons name="document-text-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('profile.termsPrivacy')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* Danger Zone */}
        <Text style={[styles.sectionTitle, { color: '#EF4444', fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.dangerZone')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card, borderColor: '#EF4444', borderWidth: 1 }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={handleDeleteAccount}
            disabled={loading}
          >
            <Ionicons name="trash-outline" size={22} color="#EF4444" style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: '#EF4444', fontFamily: 'Poppins_600SemiBold' }]}>{t('clientSettings.deleteAccountTitle')}</Text>
            {loading ? (
              <ActivityIndicator size="small" color="#EF4444" />
            ) : (
              <Ionicons name="chevron-forward" size={20} color="#EF4444" />
            )}
          </TouchableOpacity>
        </View>

        <Text style={[styles.version, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('profile.version')}</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  sectionTitle: {
    fontSize: 13,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 24,
    marginBottom: 12,
    marginLeft: 4,
  },
  section: {
    borderRadius: 12,
    marginBottom: 8,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
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
    fontSize: 15,
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    marginTop: 32,
  },
});
