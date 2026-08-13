import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

export default function ClientProfileEdit() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState('');
  const [address, setAddress] = useState('');
  const [bio, setBio] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await apiService.getClientProfile();
      setFirstName(data.first_name || data.user?.first_name || user?.firstName || '');
      setLastName(data.last_name || data.user?.last_name || user?.lastName || '');
      setPhone(data.phone_number || '');
      setCity(data.city || '');
      setAddress(data.address || '');
      setBio(data.bio || '');
    } catch (e) {
      // Fall back to auth context
      setFirstName(user?.firstName || '');
      setLastName(user?.lastName || '');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!firstName.trim() || !lastName.trim()) {
      Alert.alert('Error', 'First name and last name are required.');
      return;
    }

    setSaving(true);
    try {
      await apiService.updateClientProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone_number: phone.trim(),
        city: city.trim(),
        address: address.trim(),
        bio: bio.trim(),
      });

      if (typeof (user as any)?.updateUser === 'function') {
        (user as any).updateUser({ firstName: firstName.trim(), lastName: lastName.trim() });
      }

      Alert.alert('Success', 'Profile updated successfully.', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.response?.data?.error || 'Failed to update profile.';
      Alert.alert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flex: 1 },
    scrollContent: { padding: 20, paddingBottom: 40 },
    avatarSection: {
      alignItems: 'center', marginBottom: 28,
    },
    avatar: {
      width: 80, height: 80, borderRadius: 40,
      backgroundColor: theme.primary + '20',
      alignItems: 'center', justifyContent: 'center',
      marginBottom: 8,
    },
    avatarInitials: { fontSize: 28, fontFamily: 'Poppins_700Bold', color: theme.primary },
    avatarName: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', color: theme.text },
    avatarEmail: { fontSize: 13, fontFamily: 'Poppins_400Regular', color: theme.textSecondary, marginTop: 2 },
    card: {
      backgroundColor: theme.surface, borderRadius: 16, padding: 16, marginBottom: 16,
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
    },
    cardTitle: { fontSize: 14, fontFamily: 'Poppins_700Bold', color: theme.text, marginBottom: 14 },
    row: { flexDirection: 'row', gap: 12 },
    fieldGroup: { marginBottom: 14 },
    fieldGroupHalf: { flex: 1, marginBottom: 14 },
    label: { fontSize: 13, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginBottom: 6 },
    input: {
      backgroundColor: theme.background, borderWidth: 1.5,
      borderColor: isDark ? '#333' : '#e5e7eb',
      borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12,
      fontSize: 14, fontFamily: 'Poppins_400Regular', color: theme.text,
    },
    textArea: {
      height: 90, textAlignVertical: 'top',
    },
    saveBtn: {
      backgroundColor: theme.primary, borderRadius: 14,
      paddingVertical: 15, alignItems: 'center',
      flexDirection: 'row', justifyContent: 'center', gap: 8,
      marginTop: 8,
      shadowColor: theme.primary, shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3, shadowRadius: 8, elevation: 4,
    },
    saveBtnText: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', color: '#fff' },
    cancelBtn: { alignItems: 'center', paddingVertical: 14 },
    cancelBtnText: { fontSize: 14, fontFamily: 'Poppins_500Medium', color: theme.textSecondary },
    loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  });

  if (loading) {
    return (
      <View style={[s.container, s.loader]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  const initials = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || '?';

  return (
    <View style={s.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title="Edit Profile" />

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent} keyboardShouldPersistTaps="handled">

          {/* Avatar */}
          <View style={s.avatarSection}>
            <View style={s.avatar}>
              <Text style={s.avatarInitials}>{initials}</Text>
            </View>
            <Text style={s.avatarName}>{firstName} {lastName}</Text>
            <Text style={s.avatarEmail}>{user?.email || ''}</Text>
          </View>

          {/* Personal Info */}
          <View style={s.card}>
            <Text style={s.cardTitle}>Personal Information</Text>

            <View style={s.row}>
              <View style={s.fieldGroupHalf}>
                <Text style={s.label}>First Name *</Text>
                <TextInput
                  style={s.input}
                  value={firstName}
                  onChangeText={setFirstName}
                  placeholder="First name"
                  placeholderTextColor={theme.textSecondary}
                />
              </View>
              <View style={s.fieldGroupHalf}>
                <Text style={s.label}>Last Name *</Text>
                <TextInput
                  style={s.input}
                  value={lastName}
                  onChangeText={setLastName}
                  placeholder="Last name"
                  placeholderTextColor={theme.textSecondary}
                />
              </View>
            </View>

            <View style={s.fieldGroup}>
              <Text style={s.label}>Phone Number</Text>
              <TextInput
                style={s.input}
                value={phone}
                onChangeText={setPhone}
                placeholder="+255 7XX XXX XXX"
                placeholderTextColor={theme.textSecondary}
                keyboardType="phone-pad"
              />
            </View>

            <View style={s.fieldGroup}>
              <Text style={s.label}>Bio</Text>
              <TextInput
                style={[s.input, s.textArea]}
                value={bio}
                onChangeText={setBio}
                placeholder="Tell us a little about yourself..."
                placeholderTextColor={theme.textSecondary}
                multiline
                numberOfLines={3}
              />
            </View>
          </View>

          {/* Location */}
          <View style={s.card}>
            <Text style={s.cardTitle}>Location</Text>

            <View style={s.fieldGroup}>
              <Text style={s.label}>City</Text>
              <TextInput
                style={s.input}
                value={city}
                onChangeText={setCity}
                placeholder="e.g. Zanzibar, Dar es Salaam"
                placeholderTextColor={theme.textSecondary}
              />
            </View>

            <View style={[s.fieldGroup, { marginBottom: 0 }]}>
              <Text style={s.label}>Address</Text>
              <TextInput
                style={[s.input, s.textArea]}
                value={address}
                onChangeText={setAddress}
                placeholder="Your full address"
                placeholderTextColor={theme.textSecondary}
                multiline
                numberOfLines={2}
              />
            </View>
          </View>

          {/* Save */}
          <TouchableOpacity style={s.saveBtn} onPress={handleSave} disabled={saving}>
            {saving ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={20} color="#fff" />
                <Text style={s.saveBtnText}>Save Changes</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={s.cancelBtn} onPress={() => router.back()}>
            <Text style={s.cancelBtnText}>Cancel</Text>
          </TouchableOpacity>

        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
