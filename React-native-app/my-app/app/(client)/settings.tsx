import React, { useState } from 'react';
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
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

export default function ClientSettingsScreen() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [exportingData, setExportingData] = useState(false);

  // Notification preferences (these could be loaded from API)
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [smsNotifications, setSmsNotifications] = useState(false);

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
              setExportingData(true);
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
              setExportingData(false);
            }
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
        `• ${preview.service_requests || 0} service requests\n` +
        `• ${preview.reviews || 0} reviews\n` +
        `• ${preview.messages || 0} messages\n` +
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
      'Are you absolutely sure? Type "DELETE" to confirm.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'I Understand',
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

  const handleAnonymizeAccount = () => {
    Alert.alert(
      'Anonymize Account',
      'This will remove your personally identifiable information but keep your service history for record-keeping. You will be logged out and cannot recover this account.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Anonymize',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await apiService.anonymizeAccount();
              Alert.alert(
                'Account Anonymized',
                'Your personal information has been removed.',
                [
                  {
                    text: 'OK',
                    onPress: async () => {
                      await logout();
                    },
                  },
                ]
              );
            } catch (error: any) {
              console.error('Error anonymizing account:', error);
              Alert.alert(
                'Error',
                error.response?.data?.error || 'Failed to anonymize account. Please try again.'
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
      <Header title="Settings" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Account Settings */}
        <Text style={[styles.sectionTitle, { color: theme.textSecondary, fontFamily: 'Poppins_600SemiBold' }]}>{t('client.accountSettings')}</Text>
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/profile-edit')}
          >
            <Ionicons name="person-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('profile.editProfile')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/payment-methods')}
          >
            <Ionicons name="card-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('paymentMethods.paymentMethodsTitle')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => Alert.alert(t('profile.comingSoon'), t('clientSettings.addressManagementComingSoon'))}
          >
            <Ionicons name="location-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('client.savedAddresses')}</Text>
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
              onValueChange={setEmailNotifications}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>

          <View style={[styles.menuItem, { borderBottomColor: theme.border }]}>
            <Ionicons name="notifications-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.pushNotifications')}</Text>
            <Switch
              value={pushNotifications}
              onValueChange={setPushNotifications}
              trackColor={{ false: '#D1D5DB', true: theme.primary }}
            />
          </View>

          <View style={[styles.menuItem, { borderBottomColor: 'transparent' }]}>
            <Ionicons name="chatbox-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('privacy.smsNotifications')}</Text>
            <Switch
              value={smsNotifications}
              onValueChange={setSmsNotifications}
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
            onPress={() => Alert.alert(t('profile.comingSoon'), t('clientSettings.helpCenterComingSoon'))}
          >
            <Ionicons name="help-circle-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.helpCenter')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => Alert.alert(t('profile.comingSoon'), t('clientSettings.contactSupportComingSoon'))}
          >
            <Ionicons name="mail-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('clientSettings.contactSupport')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => Alert.alert(t('profile.comingSoon'), t('clientSettings.termsPrivacyComingSoon'))}
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
