import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

export default function WorkerProfileScreen() {
  const { user, logout } = useAuth();
  const { theme, isDark } = useTheme();
  const [isAvailable, setIsAvailable] = useState(true);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [stats, setStats] = useState({
    rating: 0,
    completedJobs: 0,
    responseRate: 0,
  });

  useEffect(() => {
    loadProfileData();
  }, []);

  const loadProfileData = async () => {
    try {
      setLoading(true);
      const [profileData, statsData] = await Promise.all([
        apiService.getWorkerProfile(),
        apiService.getWorkerStats(),
      ]);
      
      setProfile(profileData);
      setIsAvailable(profileData.availability === 'available');
      
      // Calculate stats from profile and API data
      setStats({
        rating: profileData.average_rating || 0,
        completedJobs: profileData.completed_jobs || 0,
        responseRate: statsData.response_rate || 0,
      });
    } catch (error) {
      console.error('Error loading profile:', error);
      Alert.alert('Error', 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const handleAvailabilityToggle = async (value: boolean) => {
    try {
      await apiService.updateWorkerAvailability(value);
      setIsAvailable(value);
    } catch (error) {
      console.error('Error updating availability:', error);
      Alert.alert('Error', 'Failed to update availability');
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => await logout(),
      },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <StatusBar style={theme.statusBar} />
      
      {/* Header Component */}
      <Header showBack={false} showNotifications={false} showSearch={false} />
      
      {loading ? (
        <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading profile...</Text>
        </View>
      ) : (
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Header Card */}
        <View style={[styles.profileCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          {profile?.profile_image ? (
            <Image
              source={{ uri: profile.profile_image }}
              style={styles.avatarImage}
            />
          ) : (
            <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
              <Text style={styles.avatarText}>
                {user?.firstName?.[0]}{user?.lastName?.[0]}
              </Text>
            </View>
          )}
          <Text style={[styles.name, { color: theme.text }]}>{user?.firstName} {user?.lastName}</Text>
          <Text style={[styles.email, { color: theme.textSecondary }]}>{user?.email}</Text>
          {profile && profile.categories && profile.categories.length > 0 && (
            <Text style={[styles.category, { color: theme.textTertiary }]}>
              {profile.categories.map((cat: any) => cat.name).join(' • ')}
            </Text>
          )}
        </View>

        {/* Stats Card */}
        <View style={[styles.statsCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary }]}>
              {stats.rating > 0 ? stats.rating.toFixed(1) : 'N/A'}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Rating</Text>
          </View>
          <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary }]}>{stats.completedJobs}</Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Jobs Done</Text>
          </View>
          <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary }]}>
              {stats.responseRate > 0 ? `${stats.responseRate}%` : 'N/A'}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Response</Text>
          </View>
        </View>

        {/* Availability Toggle */}
        <View style={[styles.section, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.availabilityRow}>
            <View>
              <Text style={[styles.settingTitle, { color: theme.text }]}>Available for Work</Text>
              <Text style={[styles.settingSubtitle, { color: theme.textSecondary }]}>
                Clients can see your profile
              </Text>
            </View>
            <Switch
              value={isAvailable}
              onValueChange={handleAvailabilityToggle}
              trackColor={{ false: theme.border, true: theme.primaryLight }}
              thumbColor={isAvailable ? theme.primary : theme.textTertiary}
            />
          </View>
        </View>

        {/* Menu Items */}
        <View style={[styles.section, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.divider }]}
            onPress={() => router.push('/(worker)/profile-edit')}
          >
            <Text style={styles.menuIcon}>👤</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Edit Profile</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.divider }]}
            onPress={() => router.push('/(worker)/profile-edit')}
          >
            <Text style={styles.menuIcon}>💼</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Skills & Categories</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.divider }]}
            onPress={() => router.push('/(worker)/documents')}
          >
            <Text style={styles.menuIcon}>📄</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Documents</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => router.push('/(worker)/earnings')}
          >
            <Text style={styles.menuIcon}>💰</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Earnings & Payments</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
        </View>

        <View style={[styles.section, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.divider }]}
            onPress={() => Alert.alert('Coming Soon', 'Settings feature is coming soon!')}
          >
            <Text style={styles.menuIcon}>⚙️</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Settings</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.divider }]}
            onPress={() => Alert.alert('Help & Support', 'For assistance, please contact: support@workerconnect.com')}
          >
            <Text style={styles.menuIcon}>❓</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Help & Support</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: 'transparent' }]}
            onPress={() => Alert.alert('Coming Soon', 'Terms & Privacy page is coming soon!')}
          >
            <Text style={styles.menuIcon}>📋</Text>
            <Text style={[styles.menuText, { color: theme.text }]}>Terms & Privacy</Text>
            <Text style={[styles.menuArrow, { color: theme.textTertiary }]}>›</Text>
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={[styles.logoutButton, { backgroundColor: theme.error }]} onPress={handleLogout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <Text style={[styles.version, { color: theme.textTertiary }]}>Version 1.0.0</Text>
      </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    padding: 20,
  },
  profileCard: {
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    borderWidth: 1,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarImage: {
    width: 80,
    height: 80,
    borderRadius: 40,
    marginBottom: 12,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  name: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
    marginBottom: 8,
  },
  category: {
    fontSize: 14,
    marginTop: 8,
  },
  statsCard: {
    flexDirection: 'row',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    borderWidth: 1,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
  },
  statDivider: {
    width: 1,
  },
  section: {
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    borderWidth: 1,
  },
  availabilityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  settingSubtitle: {
    fontSize: 13,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  menuIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  menuText: {
    flex: 1,
    fontSize: 15,
  },
  menuArrow: {
    fontSize: 24,
  },
  logoutButton: {
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    marginTop: 32,
    marginBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#6B7280',
  },
});
