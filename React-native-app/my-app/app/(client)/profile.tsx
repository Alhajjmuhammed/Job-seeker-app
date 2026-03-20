import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
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

export default function ClientProfileScreen() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    activeJobs: 0,
    completedJobs: 0,
    favorites: 0,
  });

  // Redirect if wrong user type
  useEffect(() => {
    if (user && user.userType !== 'client') {
      console.log('Wrong user type for client profile, redirecting to worker');
      router.replace('/(worker)/profile');
      return;
    }
    // Only load data if user type is correct
    if (user && user.userType === 'client') {
      loadProfileData();
    }
  }, [user]);

  const loadProfileData = async () => {
    try {
      setLoading(true);
      const statsData = await apiService.getClientStats();
      setStats({
        activeJobs: statsData.active_jobs,
        completedJobs: statsData.completed_jobs,
        favorites: statsData.favorites,
      });
    } catch (error) {
      console.error('Error loading profile:', error);
      Alert.alert(t('common.error'), t('profile.failedLoadProfile'));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    Alert.alert(t('nav.logout'), t('profile.sureLogout'), [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => await logout(),
      },
    ]);
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Profile" showBack={false} />

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('profile.loadingProfile')}</Text>
        </View>
      ) : (
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Info Card */}
        <View style={[styles.profileCard, { backgroundColor: theme.card }]}>
          <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
            <Text style={[styles.avatarText, { color: theme.textLight, fontFamily: 'Poppins_700Bold' }]}>
              {user?.firstName?.[0]}{user?.lastName?.[0]}
            </Text>
          </View>
          <Text style={[styles.name, { color: theme.text, fontFamily: 'Poppins_700Bold' }]}>
            {user?.firstName} {user?.lastName}
          </Text>
          <Text style={[styles.email, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{user?.email}</Text>
        </View>

        {/* Stats Card */}
        <View style={[styles.statsCard, { backgroundColor: theme.card }]}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>
              {stats.activeJobs}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('client.activeJobs')}</Text>
          </View>
          <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>
              {stats.completedJobs}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('favoriteWorkers.completedJobs')}</Text>
          </View>
          <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.primary, fontFamily: 'Poppins_700Bold' }]}>
              {stats.favorites}
            </Text>
            <Text style={[styles.statLabel, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('client.favorites')}</Text>
          </View>
        </View>

        {/* Menu Items */}
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
            onPress={() => router.push('/(client)/favorites')}
          >
            <Ionicons name="heart-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('favoriteWorkers.favoriteWorkersTitle')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
          <TouchableOpacity style={[styles.menuItem, { borderBottomColor: theme.border }]}>
            <Ionicons name="card-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('paymentMethods.paymentMethodsTitle')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
          <TouchableOpacity style={[styles.menuItem, { borderBottomColor: 'transparent' }]}>
            <Ionicons name="location-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('client.savedAddresses')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <TouchableOpacity 
            style={[styles.menuItem, { borderBottomColor: theme.border }]}
            onPress={() => router.push('/(client)/settings')}
          >
            <Ionicons name="settings-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('settings.title')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
          <TouchableOpacity style={[styles.menuItem, { borderBottomColor: theme.border }]}>
            <Ionicons name="help-circle-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('help.helpSupport')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
          <TouchableOpacity style={[styles.menuItem, { borderBottomColor: 'transparent' }]}>
            <Ionicons name="document-text-outline" size={22} color={theme.primary} style={styles.menuIcon} />
            <Text style={[styles.menuText, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>{t('profile.termsPrivacy')}</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity 
          style={[styles.logoutButton, { backgroundColor: theme.card, borderColor: '#EF4444' }]} 
          onPress={handleLogout}
        >
          <Ionicons name="log-out-outline" size={20} color="#EF4444" style={{ marginRight: 8 }} />
          <Text style={[styles.logoutText, { fontFamily: 'Poppins_600SemiBold' }]}>{t('nav.logout')}</Text>
        </TouchableOpacity>

        <Text style={[styles.version, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>{t('profile.version')}</Text>
      </ScrollView>
      )}
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
  profileCard: {
    alignItems: 'center',
    padding: 24,
    marginBottom: 16,
    borderRadius: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: {
    fontSize: 32,
  },
  name: {
    fontSize: 22,
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
  },
  statsCard: {
    flexDirection: 'row',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
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
  logoutButton: {
    flexDirection: 'row',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    borderWidth: 1,
  },
  logoutText: {
    fontSize: 16,
    color: '#EF4444',
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    marginTop: 32,
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
    color: '#1F2937',
  },
  menuArrow: {
    fontSize: 24,
    color: '#9CA3AF',
  },
});
