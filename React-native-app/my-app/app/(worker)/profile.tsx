import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useAuth } from '../../contexts/AuthContext';

export default function WorkerProfileScreen() {
  const [isAvailable, setIsAvailable] = useState(true);
  const { logout } = useAuth();

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
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>MA</Text>
        </View>
        <Text style={styles.name}>Mohammed Ahmed</Text>
        <Text style={styles.email}>mohammed@example.com</Text>
        <Text style={styles.category}>⚡ Electrician • Plumber</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Stats Card */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>4.8</Text>
            <Text style={styles.statLabel}>Rating</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>47</Text>
            <Text style={styles.statLabel}>Jobs Done</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>98%</Text>
            <Text style={styles.statLabel}>Response</Text>
          </View>
        </View>

        {/* Availability Toggle */}
        <View style={styles.section}>
          <View style={styles.availabilityRow}>
            <View>
              <Text style={styles.settingTitle}>Available for Work</Text>
              <Text style={styles.settingSubtitle}>
                Clients can see your profile
              </Text>
            </View>
            <Switch
              value={isAvailable}
              onValueChange={setIsAvailable}
              trackColor={{ false: '#D1D5DB', true: '#6EE7B7' }}
              thumbColor={isAvailable ? '#0F766E' : '#9CA3AF'}
            />
          </View>
        </View>

        {/* Menu Items */}
        <View style={styles.section}>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>👤</Text>
            <Text style={styles.menuText}>Edit Profile</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>💼</Text>
            <Text style={styles.menuText}>Skills & Categories</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>📄</Text>
            <Text style={styles.menuText}>Documents</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>💰</Text>
            <Text style={styles.menuText}>Earnings & Payments</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>⚙️</Text>
            <Text style={styles.menuText}>Settings</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>❓</Text>
            <Text style={styles.menuText}>Help & Support</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.menuItem}>
            <Text style={styles.menuIcon}>📋</Text>
            <Text style={styles.menuText}>Terms & Privacy</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <Text style={styles.version}>Version 1.0.0</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 32,
    alignItems: 'center',
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#0F766E',
  },
  name: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
    color: '#D1FAE5',
    marginBottom: 8,
  },
  category: {
    fontSize: 14,
    color: '#D1FAE5',
  },
  scrollContent: {
    padding: 20,
  },
  statsCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
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
    fontWeight: 'bold',
    color: '#0F766E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
  },
  statDivider: {
    width: 1,
    backgroundColor: '#E5E7EB',
  },
  section: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
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
    color: '#1F2937',
    marginBottom: 4,
  },
  settingSubtitle: {
    fontSize: 13,
    color: '#6B7280',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  menuIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  menuText: {
    flex: 1,
    fontSize: 15,
    color: '#1F2937',
  },
  menuArrow: {
    fontSize: 24,
    color: '#9CA3AF',
  },
  logoutButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EF4444',
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 20,
  },
});
