import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

export default function ClientProfileEditScreen() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<any>(null);

  // Form fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [country, setCountry] = useState('Tanzania');
  const [postalCode, setPostalCode] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await apiService.getClientProfile();
      setProfile(data);
      
      // Populate form fields
      setFirstName(data.first_name || '');
      setLastName(data.last_name || '');
      setPhone(data.phone_number || '');
      setCompanyName(data.company_name || '');
      setAddress(data.address || '');
      setCity(data.city || '');
      setState(data.state || '');
      setCountry(data.country || 'Tanzania');
      setPostalCode(data.postal_code || '');
    } catch (error: any) {
      console.error('Error loading profile:', error);
      Alert.alert('Error', 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validation
    if (!firstName.trim() || !lastName.trim()) {
      Alert.alert('Validation Error', 'First name and last name are required');
      return;
    }

    if (!phone.trim()) {
      Alert.alert('Validation Error', 'Phone number is required');
      return;
    }

    // Phone validation (Tanzania format +255)
    const phoneRegex = /^\+255\d{9}$/;
    if (!phoneRegex.test(phone)) {
      Alert.alert(
        'Invalid Phone',
        'Please enter a valid Tanzanian phone number (e.g., +255712345678)'
      );
      return;
    }

    try {
      setSaving(true);
      
      const updateData = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone_number: phone.trim(),
        company_name: companyName.trim(),
        address: address.trim(),
        city: city.trim(),
        state: state.trim(),
        country: country,
        postal_code: postalCode.trim(),
      };

      await apiService.updateClientProfile(updateData);
      
      Alert.alert(
        'Success',
        'Profile updated successfully',
        [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
    } catch (error: any) {
      console.error('Error saving profile:', error);
      Alert.alert(
        'Save Error',
        error.response?.data?.error || 'Failed to update profile. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <StatusBar style={theme.statusBar} />
        <Header title="Edit Profile" />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
            Loading profile...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header title="Edit Profile" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Personal Information */}
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="person-outline" size={24} color={theme.primary} />
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
              Personal Information
            </Text>
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              First Name *
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.text,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={firstName}
              onChangeText={setFirstName}
              placeholder="Enter first name"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              Last Name *
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.text,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={lastName}
              onChangeText={setLastName}
              placeholder="Enter last name"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              Phone Number *
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.text,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={phone}
              onChangeText={setPhone}
              placeholder="+255712345678"
              placeholderTextColor={theme.textSecondary}
              keyboardType="phone-pad"
            />
            <Text style={[styles.hint, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              Format: +255XXXXXXXXX
            </Text>
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              Email
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.textSecondary,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={profile?.email || ''}
              editable={false}
              placeholder="Email address"
              placeholderTextColor={theme.textSecondary}
            />
            <Text style={[styles.hint, { color: theme.textSecondary, fontFamily: 'Poppins_400Regular' }]}>
              Email cannot be changed
            </Text>
          </View>
        </View>

        {/* Company Information */}
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="business-outline" size={24} color={theme.primary} />
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
              Company Information (Optional)
            </Text>
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              Company Name
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.text,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={companyName}
              onChangeText={setCompanyName}
              placeholder="Enter company name"
              placeholderTextColor={theme.textSecondary}
            />
          </View>
        </View>

        {/* Address Information */}
        <View style={[styles.section, { backgroundColor: theme.card }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="location-outline" size={24} color={theme.primary} />
            <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: 'Poppins_600SemiBold' }]}>
              Address
            </Text>
          </View>

          <View style={styles.inputGroup}>
            <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
              Street Address
            </Text>
            <TextInput
              style={[styles.input, { 
                backgroundColor: theme.surface, 
                color: theme.text,
                borderColor: theme.border,
                fontFamily: 'Poppins_400Regular'
              }]}
              value={address}
              onChangeText={setAddress}
              placeholder="Enter street address"
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={2}
            />
          </View>

          <View style={styles.row}>
            <View style={[styles.inputGroup, { flex: 1, marginRight: 8 }]}>
              <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                City
              </Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: theme.surface, 
                  color: theme.text,
                  borderColor: theme.border,
                  fontFamily: 'Poppins_400Regular'
                }]}
                value={city}
                onChangeText={setCity}
                placeholder="City"
                placeholderTextColor={theme.textSecondary}
              />
            </View>

            <View style={[styles.inputGroup, { flex: 1, marginLeft: 8 }]}>
              <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                State/Region
              </Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: theme.surface, 
                  color: theme.text,
                  borderColor: theme.border,
                  fontFamily: 'Poppins_400Regular'
                }]}
                value={state}
                onChangeText={setState}
                placeholder="State"
                placeholderTextColor={theme.textSecondary}
              />
            </View>
          </View>

          <View style={styles.row}>
            <View style={[styles.inputGroup, { flex: 1, marginRight: 8 }]}>
              <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                Country
              </Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: theme.surface, 
                  color: theme.text,
                  borderColor: theme.border,
                  fontFamily: 'Poppins_400Regular'
                }]}
                value={country}
                onChangeText={setCountry}
                placeholder="Country"
                placeholderTextColor={theme.textSecondary}
              />
            </View>

            <View style={[styles.inputGroup, { flex: 1, marginLeft: 8 }]}>
              <Text style={[styles.label, { color: theme.text, fontFamily: 'Poppins_500Medium' }]}>
                Postal Code
              </Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: theme.surface, 
                  color: theme.text,
                  borderColor: theme.border,
                  fontFamily: 'Poppins_400Regular'
                }]}
                value={postalCode}
                onChangeText={setPostalCode}
                placeholder="Postal"
                placeholderTextColor={theme.textSecondary}
                keyboardType="number-pad"
              />
            </View>
          </View>
        </View>

        {/* Save Button */}
        <TouchableOpacity
          style={[styles.saveButton, { backgroundColor: theme.primary }]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="checkmark-circle-outline" size={20} color="#FFFFFF" />
              <Text style={[styles.saveButtonText, { fontFamily: 'Poppins_600SemiBold' }]}>
                Save Changes
              </Text>
            </>
          )}
        </TouchableOpacity>
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
    paddingVertical: 40,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  section: {
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    gap: 12,
  },
  sectionTitle: {
    fontSize: 16,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
  },
  hint: {
    fontSize: 12,
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
    marginBottom: 0,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
    gap: 8,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
  },
});
