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
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { Picker } from '@react-native-picker/picker';
import { useAuth } from '../../contexts/AuthContext';
import apiService from '../../services/api';

type Category = {
  id: number;
  name: string;
  description: string;
  icon: string;
};

export default function ProfileEditScreen() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<any>(null);
  const [categories, setCategories] = useState<Category[]>([]);

  // Form fields
  const [bio, setBio] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [country, setCountry] = useState('Sudan');
  const [postalCode, setPostalCode] = useState('');
  const [religion, setReligion] = useState('');
  const [canWorkEverywhere, setCanWorkEverywhere] = useState(false);
  const [experienceYears, setExperienceYears] = useState('0');
  const [hourlyRate, setHourlyRate] = useState('');
  const [availability, setAvailability] = useState('available');
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      const [profileData, categoriesData] = await Promise.all([
        apiService.getWorkerProfile(),
        apiService.getCategories(),
      ]);

      setProfile(profileData);
      setCategories(categoriesData);

      // Populate form fields
      setBio(profileData.bio || '');
      setPhone(profileData.phone_number || '');
      setAddress(profileData.address || '');
      setCity(profileData.city || '');
      setState(profileData.state || '');
      setCountry(profileData.country || 'Sudan');
      setPostalCode(profileData.postal_code || '');
      setReligion(profileData.religion || '');
      setCanWorkEverywhere(profileData.can_work_everywhere || false);
      setExperienceYears(String(profileData.experience_years || 0));
      setHourlyRate(profileData.hourly_rate ? String(profileData.hourly_rate) : '');
      setAvailability(profileData.availability || 'available');
      setSelectedCategories(profileData.categories?.map((c: any) => c.id) || []);
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      Alert.alert('Error', 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const handlePickImage = async () => {
    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (permissionResult.granted === false) {
      Alert.alert('Permission Required', 'Please allow access to your photo library');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });

    if (!result.canceled) {
      uploadProfileImage(result.assets[0]);
    }
  };

  const uploadProfileImage = async (image: any) => {
    try {
      setSaving(true);
      
      // Get proper MIME type from file extension or URI
      const getImageType = (uri: string) => {
        const ext = uri.split('.').pop()?.toLowerCase();
        const mimeTypes: { [key: string]: string } = {
          'jpg': 'image/jpeg',
          'jpeg': 'image/jpeg',
          'png': 'image/png',
          'gif': 'image/gif',
          'webp': 'image/webp',
        };
        return mimeTypes[ext || 'jpg'] || 'image/jpeg';
      };
      
      // For iOS/React Native, we need to ensure proper file format
      const imageType = getImageType(image.uri);
      const fileName = image.fileName || image.uri.split('/').pop() || 'profile.jpg';
      
      // Create FormData - React Native specific format
      const formData: any = new FormData();
      formData.append('profile_image', {
        uri: image.uri,
        type: imageType,
        name: fileName,
      });
      
      console.log('Uploading image:', { uri: image.uri, type: imageType, name: fileName });

      const response = await apiService.updateWorkerProfile(formData);
      console.log('Upload response:', response);
      
      // Update profile state immediately with the new image
      setProfile((prev: any) => ({
        ...prev,
        profile_image: response.profile_image
      }));
      
      Alert.alert('Success', 'Profile photo updated!');
      // Fetch full profile data to update everything
      await fetchProfileData();
    } catch (error: any) {
      console.error('Failed to upload image:', error);
      console.error('Error response:', error?.response?.data);
      
      let errorMsg = 'Failed to upload profile photo';
      if (error?.response?.data?.profile_image) {
        errorMsg = error.response.data.profile_image[0];
      } else if (error?.response?.data?.error) {
        errorMsg = error.response.data.error;
      } else if (error?.message) {
        errorMsg = error.message;
      }
      
      Alert.alert('Upload Error', errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const toggleCategory = (categoryId: number) => {
    setSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);

      const data = {
        bio,
        address,
        city,
        state,
        country,
        postal_code: postalCode,
        religion,
        can_work_everywhere: canWorkEverywhere,
        experience_years: parseInt(experienceYears) || 0,
        hourly_rate: hourlyRate ? parseFloat(hourlyRate) : null,
        availability,
        category_ids: selectedCategories,
      };

      await apiService.updateWorkerProfile(data);
      Alert.alert('Success', 'Profile updated successfully!', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } catch (error: any) {
      console.error('Failed to save profile:', error);
      Alert.alert('Error', error.response?.data?.error || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0F766E" />
        <Text style={styles.loadingText}>Loading profile...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Edit Profile</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Profile Completion */}
        {profile && (
          <View style={styles.completionCard}>
            <View style={styles.completionHeader}>
              <Text style={styles.completionTitle}>Profile Completion</Text>
              <Text style={styles.completionPercent}>
                {profile.profile_completion_percentage || 0}%
              </Text>
            </View>
            <View style={styles.progressBar}>
              <View 
                style={[
                  styles.progressFill, 
                  { width: `${profile.profile_completion_percentage || 0}%` }
                ]} 
              />
            </View>
          </View>
        )}

        {/* Profile Photo Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="camera" size={24} color="#0F766E" />
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitle}>Profile Photo</Text>
              <Text style={styles.sectionSubtitle}>Upload a professional photo</Text>
            </View>
          </View>

          <View style={styles.photoContainer}>
            {profile?.profile_image ? (
              <Image source={{ uri: profile.profile_image }} style={styles.profileImage} />
            ) : (
              <View style={styles.profilePlaceholder}>
                <Text style={styles.placeholderText}>
                  {user?.firstName?.[0]}{user?.lastName?.[0]}
                </Text>
              </View>
            )}
            <TouchableOpacity 
              style={styles.changePhotoButton} 
              onPress={handlePickImage}
              disabled={saving}
            >
              <Ionicons name="camera" size={20} color="#FFF" />
              <Text style={styles.changePhotoText}>
                {profile?.profile_image ? 'Change Photo' : 'Upload Photo'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Personal Information */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="person" size={24} color="#0F766E" />
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitle}>Personal Information</Text>
              <Text style={styles.sectionSubtitle}>Tell us about yourself</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Bio</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={bio}
              onChangeText={setBio}
              placeholder="Write a brief introduction about your skills and experience"
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Phone Number</Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="+255712345678"
              keyboardType="phone-pad"
              editable={false}
            />
            <Text style={styles.helpText}>Phone cannot be changed</Text>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Email Address</Text>
            <TextInput
              style={[styles.input, styles.disabledInput]}
              value={user?.email}
              editable={false}
            />
            <Text style={styles.helpText}>Email cannot be changed</Text>
          </View>
        </View>

        {/* Location */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="location" size={24} color="#0F766E" />
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitle}>Location</Text>
              <Text style={styles.sectionSubtitle}>Where are you based?</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Address</Text>
            <TextInput
              style={styles.input}
              value={address}
              onChangeText={setAddress}
              placeholder="Street address"
            />
          </View>

          <View style={styles.row}>
            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={styles.label}>City</Text>
              <TextInput
                style={styles.input}
                value={city}
                onChangeText={setCity}
                placeholder="City"
              />
            </View>

            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={styles.label}>State/Province</Text>
              <TextInput
                style={styles.input}
                value={state}
                onChangeText={setState}
                placeholder="State"
              />
            </View>
          </View>

          <View style={styles.row}>
            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={styles.label}>Country</Text>
              <View style={styles.pickerContainer}>
                <Picker
                  selectedValue={country}
                  onValueChange={setCountry}
                  style={styles.picker}
                >
                  <Picker.Item label="Sudan" value="Sudan" />
                  <Picker.Item label="Tanzania" value="Tanzania" />
                  <Picker.Item label="Kenya" value="Kenya" />
                  <Picker.Item label="Uganda" value="Uganda" />
                  <Picker.Item label="Rwanda" value="Rwanda" />
                  <Picker.Item label="Burundi" value="Burundi" />
                  <Picker.Item label="South Sudan" value="South Sudan" />
                  <Picker.Item label="Somalia" value="Somalia" />
                  <Picker.Item label="Ethiopia" value="Ethiopia" />
                  <Picker.Item label="Djibouti" value="Djibouti" />
                  <Picker.Item label="Eritrea" value="Eritrea" />
                </Picker>
              </View>
            </View>

            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={styles.label}>Postal Code</Text>
              <TextInput
                style={styles.input}
                value={postalCode}
                onChangeText={setPostalCode}
                placeholder="Postal code"
              />
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Religion (Optional)</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={religion}
                onValueChange={setReligion}
                style={styles.picker}
              >
                <Picker.Item label="Prefer not to say" value="" />
                <Picker.Item label="Islam" value="islam" />
                <Picker.Item label="Christianity" value="christianity" />
                <Picker.Item label="Judaism" value="judaism" />
                <Picker.Item label="Hinduism" value="hinduism" />
                <Picker.Item label="Buddhism" value="buddhism" />
                <Picker.Item label="Sikhism" value="sikhism" />
                <Picker.Item label="Other" value="other" />
              </Picker>
            </View>
          </View>

          <TouchableOpacity
            style={styles.checkboxRow}
            onPress={() => setCanWorkEverywhere(!canWorkEverywhere)}
            activeOpacity={0.7}
          >
            <View style={[
              styles.checkbox,
              canWorkEverywhere && styles.checkboxChecked
            ]}>
              {canWorkEverywhere && (
                <Ionicons name="checkmark" size={16} color="#FFF" />
              )}
            </View>
            <Text style={styles.checkboxLabel}>
              Can work everywhere (any location)
            </Text>
          </TouchableOpacity>
        </View>

        {/* Professional Details */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="briefcase" size={24} color="#0F766E" />
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitle}>Professional Details</Text>
              <Text style={styles.sectionSubtitle}>Your skills and rates</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Years of Experience</Text>
            <TextInput
              style={styles.input}
              value={experienceYears}
              onChangeText={setExperienceYears}
              placeholder="0"
              keyboardType="numeric"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Hourly Rate (USD)</Text>
            <View style={styles.inputWithPrefix}>
              <Text style={styles.inputPrefix}>$</Text>
              <TextInput
                style={[styles.input, styles.inputWithPrefixField]}
                value={hourlyRate}
                onChangeText={setHourlyRate}
                placeholder="0.00"
                keyboardType="decimal-pad"
              />
            </View>
            <Text style={styles.helpText}>Your hourly rate in US dollars</Text>
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Availability</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={availability}
                onValueChange={setAvailability}
                style={styles.picker}
              >
                <Picker.Item label="Available" value="available" />
                <Picker.Item label="Busy" value="busy" />
                <Picker.Item label="Offline" value="offline" />
              </Picker>
            </View>
          </View>
        </View>

        {/* Categories */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="pricetags" size={24} color="#0F766E" />
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitle}>Categories</Text>
              <Text style={styles.sectionSubtitle}>Select your work categories</Text>
            </View>
          </View>

          <View style={styles.categoriesGrid}>
            {categories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryItem,
                  selectedCategories.includes(category.id) && styles.categoryItemSelected,
                ]}
                onPress={() => toggleCategory(category.id)}
                activeOpacity={0.7}
              >
                <View style={[
                  styles.categoryCheckbox,
                  selectedCategories.includes(category.id) && styles.categoryCheckboxChecked
                ]}>
                  {selectedCategories.includes(category.id) && (
                    <Ionicons name="checkmark" size={16} color="#FFF" />
                  )}
                </View>
                <Text
                  style={[
                    styles.categoryLabel,
                    selectedCategories.includes(category.id) && styles.categoryLabelSelected,
                  ]}
                >
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Save Button */}
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.saveButton, saving && styles.disabledButton]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={20} color="#FFF" />
                <Text style={styles.saveButtonText}>Save Changes</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => router.back()}
            disabled={saving}
          >
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F3F4F6',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  scrollView: {
    flex: 1,
  },
  completionCard: {
    backgroundColor: '#0F766E15',
    margin: 20,
    padding: 20,
    borderRadius: 12,
  },
  completionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  completionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  completionPercent: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0F766E',
  },
  progressBar: {
    height: 10,
    backgroundColor: '#FFF',
    borderRadius: 20,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#0F766E',
    borderRadius: 20,
  },
  section: {
    backgroundColor: '#FFF',
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    gap: 12,
  },
  sectionTitleContainer: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  sectionSubtitle: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 2,
  },
  photoContainer: {
    alignItems: 'center',
    gap: 16,
  },
  profileImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
  },
  profilePlaceholder: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#0F766E',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFF',
  },
  changePhotoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#0F766E',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  changePhotoText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    backgroundColor: '#FFF',
  },
  textArea: {
    minHeight: 100,
    paddingTop: 12,
  },
  disabledInput: {
    backgroundColor: '#F9FAFB',
    color: '#9CA3AF',
  },
  helpText: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  halfWidth: {
    flex: 1,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 8,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginTop: 8,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#0F766E',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFF',
  },
  checkboxChecked: {
    backgroundColor: '#0F766E',
  },
  checkboxLabel: {
    fontSize: 14,
    color: '#4B5563',
    flex: 1,
  },
  inputWithPrefix: {
    position: 'relative',
  },
  inputPrefix: {
    position: 'absolute',
    left: 12,
    top: 12,
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
    zIndex: 1,
  },
  inputWithPrefixField: {
    paddingLeft: 32,
  },
  categoriesGrid: {
    gap: 12,
  },
  categoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    backgroundColor: '#F9FAFB',
    borderRadius: 10,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  categoryItemSelected: {
    backgroundColor: '#F0FDF4',
    borderColor: '#86EFAC',
  },
  categoryCheckbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#0F766E',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFF',
  },
  categoryCheckboxChecked: {
    backgroundColor: '#0F766E',
  },
  categoryLabel: {
    fontSize: 15,
    color: '#4B5563',
    flex: 1,
  },
  categoryLabelSelected: {
    color: '#065F46',
    fontWeight: '600',
  },
  actions: {
    marginHorizontal: 20,
    marginTop: 8,
    gap: 12,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#0F766E',
    paddingVertical: 16,
    borderRadius: 12,
  },
  saveButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  disabledButton: {
    opacity: 0.6,
  },
  cancelButton: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  cancelButtonText: {
    color: '#6B7280',
    fontSize: 16,
    fontWeight: '500',
  },
});
