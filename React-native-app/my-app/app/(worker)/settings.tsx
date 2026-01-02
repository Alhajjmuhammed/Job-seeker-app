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
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import Header from '../../components/Header';

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
  const { theme, isDark } = useTheme();
  const { user, logout } = useAuth();
  
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
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const savePrivacySettings = async (newSettings: PrivacySettings) => {
    try {
      await AsyncStorage.setItem('privacySettings', JSON.stringify(newSettings));
      setPrivacySettings(newSettings);
    } catch (error) {
      console.error('Error saving privacy settings:', error);
      Alert.alert('Error', 'Failed to save settings');
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

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'Are you sure you want to delete your account? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            Alert.alert('Coming Soon', 'Account deletion will be available soon');
          },
        },
      ]
    );
  };

  const handleLanguageChange = () => {
    Alert.alert(
      'Select Language',
      'Choose your preferred language',
      [
        { text: 'English', onPress: () => {} },
        { text: 'Spanish', onPress: () => Alert.alert('Coming Soon', 'Spanish language support coming soon') },
        { text: 'French', onPress: () => Alert.alert('Coming Soon', 'French language support coming soon') },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title="Settings" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Account Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Account</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleLanguageChange}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="language-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>Language</Text>
              </View>
              <View style={styles.settingRight}>
                <Text style={[styles.settingValue, { color: theme.textSecondary }]}>English</Text>
                <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
              </View>
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.settingRow}
              onPress={() => Alert.alert('Coming Soon', 'Payment methods management coming soon')}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="card-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>Payment Methods</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Notification Settings */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Notifications</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="notifications-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>Push Notifications</Text>
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
                <Text style={[styles.settingText, { color: theme.text }]}>Email Notifications</Text>
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
                <Text style={[styles.settingText, { color: theme.text }]}>SMS Notifications</Text>
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
              <Text style={[styles.settingText, { color: theme.text }]}>Job Alerts</Text>
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
              <Text style={[styles.settingText, { color: theme.text }]}>Message Alerts</Text>
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
              <Text style={[styles.settingText, { color: theme.text }]}>Application Updates</Text>
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
              <Text style={[styles.settingText, { color: theme.text }]}>Marketing Emails</Text>
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
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Privacy</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <View style={styles.settingRow}>
              <View style={styles.settingLeft}>
                <Ionicons name="eye-outline" size={24} color={theme.primary} />
                <Text style={[styles.settingText, { color: theme.text }]}>Profile Visible</Text>
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
                <Text style={[styles.settingText, { color: theme.text }]}>Show Location</Text>
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
                <Text style={[styles.settingText, { color: theme.text }]}>Show Phone Number</Text>
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
                <Text style={[styles.settingText, { color: theme.text }]}>Allow Direct Messages</Text>
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

        {/* Danger Zone */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: '#EF4444' }]}>Danger Zone</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.settingRow}
              onPress={handleLogout}
            >
              <View style={styles.settingLeft}>
                <Ionicons name="log-out-outline" size={24} color="#F59E0B" />
                <Text style={[styles.settingText, { color: '#F59E0B' }]}>Logout</Text>
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
                <Text style={[styles.settingText, { color: '#EF4444' }]}>Delete Account</Text>
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
});
