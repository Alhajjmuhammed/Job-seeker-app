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
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

type Category = {
  id: number;
  name: string;
  description: string;
  icon: string;
};

type Skill = {
  id: number;
  name: string;
  category: number;
};

export default function ProfileEditScreen() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<any>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [allSkills, setAllSkills] = useState<Skill[]>([]);

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
  const [workerType, setWorkerType] = useState<'professional' | 'non_academic'>('non_academic');
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<number[]>([]);

  // Dynamic styles using theme
  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.background,
    },
    loadingText: {
      marginTop: 12,
      fontSize: 16,
      fontFamily: 'Poppins_400Regular',
      color: theme.textSecondary,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: theme.primary,
      paddingTop: 60,
      paddingBottom: 20,
      paddingHorizontal: 20,
    },
    backButton: {
      padding: 8,
    },
    headerTitle: {
      fontSize: 20,
      fontFamily: 'Poppins_700Bold',
      color: '#FFFFFF',
    },
    scrollView: {
      flex: 1,
    },
    completionCard: {
      backgroundColor: isDark ? 'rgba(15, 118, 110, 0.1)' : '#0F766E15',
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
      fontFamily: 'Poppins_600SemiBold',
      color: theme.text,
    },
    completionPercent: {
      fontSize: 20,
      fontFamily: 'Poppins_700Bold',
      color: theme.primary,
    },
    progressBar: {
      height: 10,
      backgroundColor: isDark ? theme.surface : '#FFF',
      borderRadius: 20,
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      backgroundColor: theme.primary,
      borderRadius: 20,
    },
    section: {
      backgroundColor: theme.surface,
      marginHorizontal: 20,
      marginBottom: 16,
      padding: 20,
      borderRadius: 12,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
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
      fontFamily: 'Poppins_700Bold',
      color: theme.text,
    },
    sectionSubtitle: {
      fontSize: 13,
      fontFamily: 'Poppins_400Regular',
      color: theme.textSecondary,
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
      backgroundColor: theme.primary,
      justifyContent: 'center',
      alignItems: 'center',
    },
    placeholderText: {
      fontSize: 48,
      fontFamily: 'Poppins_700Bold',
      color: '#FFF',
    },
    changePhotoButton: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
      backgroundColor: theme.primary,
      paddingVertical: 12,
      paddingHorizontal: 24,
      borderRadius: 8,
    },
    changePhotoText: {
      color: '#FFF',
      fontSize: 14,
      fontFamily: 'Poppins_600SemiBold',
    },
    formGroup: {
      marginBottom: 16,
    },
    label: {
      fontSize: 14,
      fontFamily: 'Poppins_600SemiBold',
      color: theme.text,
      marginBottom: 8,
    },
    input: {
      borderWidth: 1,
      borderColor: theme.border,
      borderRadius: 8,
      padding: 12,
      fontSize: 14,
      fontFamily: 'Poppins_400Regular',
      backgroundColor: theme.surface,
      color: theme.text,
    },
    textArea: {
      minHeight: 100,
      paddingTop: 12,
    },
    disabledInput: {
      backgroundColor: isDark ? theme.surface : '#F9FAFB',
      color: theme.textSecondary,
    },
    helpText: {
      fontSize: 12,
      fontFamily: 'Poppins_400Regular',
      color: theme.textSecondary,
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
      borderColor: theme.border,
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
      borderColor: theme.primary,
      borderRadius: 6,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.surface,
    },
    checkboxChecked: {
      backgroundColor: theme.primary,
    },
    checkboxLabel: {
      fontSize: 14,
      fontFamily: 'Poppins_400Regular',
      color: theme.text,
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
      fontFamily: 'Poppins_600SemiBold',
      color: theme.textSecondary,
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
      backgroundColor: isDark ? theme.surface : '#F9FAFB',
      borderRadius: 10,
      borderWidth: 2,
      borderColor: 'transparent',
    },
    categoryItemSelected: {
      backgroundColor: isDark ? 'rgba(15, 118, 110, 0.2)' : '#F0FDF4',
      borderColor: theme.primary,
    },
    categoryCheckbox: {
      width: 24,
      height: 24,
      borderWidth: 2,
      borderColor: theme.primary,
      borderRadius: 6,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.surface,
    },
    categoryCheckboxChecked: {
      backgroundColor: theme.primary,
    },
    categoryLabel: {
      fontSize: 15,
      fontFamily: 'Poppins_400Regular',
      color: theme.text,
      flex: 1,
    },
    categoryLabelSelected: {
      color: theme.primary,
      fontFamily: 'Poppins_600SemiBold',
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
      backgroundColor: theme.primary,
      paddingVertical: 16,
      borderRadius: 12,
    },
    saveButtonText: {
      color: '#FFF',
      fontSize: 16,
      fontFamily: 'Poppins_600SemiBold',
    },
    disabledButton: {
      opacity: 0.6,
    },
    cancelButton: {
      alignItems: 'center',
      paddingVertical: 16,
    },
    cancelButtonText: {
      color: theme.textSecondary,
      fontSize: 16,
      fontFamily: 'Poppins_500Medium',
    },
  });

  useEffect(() => {
    fetchProfileData();
  }, []);

  useEffect(() => {
    // Fetch skills when categories change
    if (selectedCategories.length > 0) {
      fetchSkills();
    } else {
      setAllSkills([]);
      setSelectedSkills([]);
    }
  }, [selectedCategories]);

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
      setWorkerType(profileData.worker_type || 'non_academic');
      setSelectedCategories(profileData.categories?.map((c: any) => c.id) || []);
      setSelectedSkills(profileData.skills?.map((s: any) => s.id) || []);
      
      // Fetch initial skills if categories exist
      if (profileData.categories && profileData.categories.length > 0) {
        const categoryIds = profileData.categories.map((c: any) => c.id);
        const skillsData = await apiService.getSkills(categoryIds);
        setAllSkills(skillsData);
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      Alert.alert('Error', 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const fetchSkills = async () => {
    try {
      const skillsData = await apiService.getSkills(selectedCategories);
      setAllSkills(skillsData);
      // Clear selected skills that don't belong to current categories
      setSelectedSkills(prev => 
        prev.filter(skillId => 
          skillsData.some((skill: Skill) => skill.id === skillId)
        )
      );
    } catch (error) {
      console.error('Failed to fetch skills:', error);
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

  const toggleSkill = (skillId: number) => {
    setSelectedSkills(prev =>
      prev.includes(skillId)
        ? prev.filter(id => id !== skillId)
        : [...prev, skillId]
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
        worker_type: workerType,
        category_ids: selectedCategories,
        skill_ids: selectedSkills,
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
      <View style={[styles.loadingContainer, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading profile...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />

      {/* Header Component */}
      <Header 
        showBack
      />

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Profile Completion */}
        {profile && (
          <View style={[styles.completionCard, { backgroundColor: isDark ? 'rgba(15, 118, 110, 0.1)' : '#0F766E15' }]}>
            <View style={styles.completionHeader}>
              <Text style={[styles.completionTitle, { color: theme.text }]}>Profile Completion</Text>
              <Text style={[styles.completionPercent, { color: theme.primary }]}>
                {profile.profile_completion_percentage || 0}%
              </Text>
            </View>
            <View style={[styles.progressBar, { backgroundColor: theme.surface }]}>
              <View 
                style={[
                  styles.progressFill, 
                  { width: `${profile.profile_completion_percentage || 0}%`, backgroundColor: theme.primary }
                ]} 
              />
            </View>
          </View>
        )}

        {/* Profile Photo Section */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="camera" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Profile Photo</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>Upload a professional photo</Text>
            </View>
          </View>

          <View style={styles.photoContainer}>
            {profile?.profile_image ? (
              <Image source={{ uri: profile.profile_image }} style={styles.profileImage} />
            ) : (
              <View style={[styles.profilePlaceholder, { backgroundColor: theme.primary }]}>
                <Text style={styles.placeholderText}>
                  {user?.firstName?.[0]}{user?.lastName?.[0]}
                </Text>
              </View>
            )}
            <TouchableOpacity 
              style={[styles.changePhotoButton, { backgroundColor: theme.primary }]} 
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
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="person" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Personal Information</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>Tell us about yourself</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Bio</Text>
            <TextInput
              style={[styles.input, styles.textArea, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={bio}
              onChangeText={setBio}
              placeholder="Write a brief introduction about your skills and experience"
              placeholderTextColor={theme.textSecondary}
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Phone Number</Text>
            <TextInput
            style={[styles.input, { backgroundColor: isDark ? theme.surface : '#F9FAFB', borderColor: theme.border, color: theme.text }]}
              value={phone}
              onChangeText={setPhone}
              placeholder="+255712345678"
              placeholderTextColor={theme.textSecondary}
              keyboardType="phone-pad"
              editable={false}
            />
            <Text style={[styles.helpText, { color: theme.textSecondary }]}>Phone cannot be changed</Text>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Email Address</Text>
            <TextInput
              style={[styles.input, styles.disabledInput, { backgroundColor: isDark ? theme.surface : '#F9FAFB', borderColor: theme.border, color: theme.text }]}
              value={user?.email}
              editable={false}
            />
            <Text style={[styles.helpText, { color: theme.textSecondary }]}>Email cannot be changed</Text>
          </View>
        </View>

        {/* Location */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="location" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Location</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>Where are you based?</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Address</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={address}
              onChangeText={setAddress}
              placeholder="Street address"
              placeholderTextColor={theme.textSecondary}
            />
          </View>

          <View style={styles.row}>
            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={[styles.label, { color: theme.text }]}>City</Text>
              <TextInput
                style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
                value={city}
                onChangeText={setCity}
                placeholder="City"
                placeholderTextColor={theme.textSecondary}
              />
            </View>

            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={[styles.label, { color: theme.text }]}>State/Province</Text>
              <TextInput
                style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
                value={state}
                onChangeText={setState}
                placeholder="State"
                placeholderTextColor={theme.textSecondary}
              />
            </View>
          </View>

          <View style={styles.row}>
            <View style={[styles.formGroup, styles.halfWidth]}>
              <Text style={[styles.label, { color: theme.text }]}>Country</Text>
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
              <Text style={[styles.label, { color: theme.text }]}>Postal Code</Text>
              <TextInput
                style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
                value={postalCode}
                onChangeText={setPostalCode}
                placeholder="Postal code"
                placeholderTextColor={theme.textSecondary}
              />
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Religion (Optional)</Text>
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
              { borderColor: theme.primary, backgroundColor: theme.surface },
              canWorkEverywhere && { backgroundColor: theme.primary }
            ]}>
              {canWorkEverywhere && (
                <Ionicons name="checkmark" size={16} color="#FFF" />
              )}
            </View>
            <Text style={[styles.checkboxLabel, { color: theme.text }]}>
              Can work everywhere (any location)
            </Text>
          </TouchableOpacity>
        </View>

        {/* Professional Details */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="briefcase" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Professional Details</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>Your skills and rates</Text>
            </View>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Years of Experience</Text>
            <TextInput
              style={[styles.input, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
              value={experienceYears}
              onChangeText={setExperienceYears}
              placeholder="0"
              placeholderTextColor={theme.textSecondary}
              keyboardType="numeric"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Hourly Rate (USD)</Text>
            <View style={styles.inputWithPrefix}>
              <Text style={[styles.inputPrefix, { color: theme.textSecondary }]}>$</Text>
              <TextInput
                style={[styles.input, styles.inputWithPrefixField, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text }]}
                value={hourlyRate}
                onChangeText={setHourlyRate}
                placeholder="0.00"
                placeholderTextColor={theme.textSecondary}
                keyboardType="decimal-pad"
              />
            </View>
            <Text style={[styles.helpText, { color: theme.textSecondary }]}>Your hourly rate in US dollars</Text>
          </View>

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Availability</Text>
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

          <View style={styles.formGroup}>
            <Text style={[styles.label, { color: theme.text }]}>Worker Type</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={workerType}
                onValueChange={(value) => setWorkerType(value as 'professional' | 'non_academic')}
                style={styles.picker}
              >
                <Picker.Item label="Professional (Can apply for jobs)" value="professional" />
                <Picker.Item label="Non-Academic (Direct hire only)" value="non_academic" />
              </Picker>
            </View>
            <Text style={[styles.helpText, { color: theme.textSecondary }]}>
              {workerType === 'professional' 
                ? 'You can browse and apply for jobs in your field' 
                : 'You will receive direct hire requests from clients'}
            </Text>
          </View>
        </View>

        {/* Categories */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="pricetags" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Categories</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>Select your work categories</Text>
            </View>
          </View>

          <View style={styles.categoriesGrid}>
            {categories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryItem,
                  { backgroundColor: theme.surface, borderColor: theme.border },
                  selectedCategories.includes(category.id) && { backgroundColor: isDark ? 'rgba(15, 118, 110, 0.2)' : '#F0FDF4', borderColor: theme.primary },
                ]}
                onPress={() => toggleCategory(category.id)}
                activeOpacity={0.7}
              >
                <View style={[
                  styles.categoryCheckbox,
                  { borderColor: theme.primary, backgroundColor: theme.surface },
                  selectedCategories.includes(category.id) && { backgroundColor: theme.primary }
                ]}>
                  {selectedCategories.includes(category.id) && (
                    <Ionicons name="checkmark" size={16} color="#FFF" />
                  )}
                </View>
                <Text
                  style={[
                    styles.categoryLabel,
                    { color: theme.text },
                    selectedCategories.includes(category.id) && { color: theme.primary, fontFamily: 'Poppins_600SemiBold' },
                  ]}
                >
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Skills Section - Only show if categories are selected */}
        {selectedCategories.length > 0 && allSkills.length > 0 && (
          <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
            <View style={styles.sectionHeader}>
              <Ionicons name="construct" size={24} color={theme.primary} />
              <View style={styles.sectionTitleContainer}>
                <Text style={[styles.sectionTitle, { color: theme.text }]}>Skills</Text>
                <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>
                  Select your skills ({selectedSkills.length} selected)
                </Text>
              </View>
            </View>

            <View style={styles.categoriesGrid}>
              {allSkills.map((skill) => (
                <TouchableOpacity
                  key={skill.id}
                  style={[
                    styles.categoryItem,
                    { backgroundColor: theme.surface, borderColor: theme.border },
                    selectedSkills.includes(skill.id) && { backgroundColor: isDark ? 'rgba(15, 118, 110, 0.2)' : '#F0FDF4', borderColor: theme.primary },
                  ]}
                  onPress={() => toggleSkill(skill.id)}
                  activeOpacity={0.7}
                >
                  <View style={[
                    styles.categoryCheckbox,
                    { borderColor: theme.primary, backgroundColor: theme.surface },
                    selectedSkills.includes(skill.id) && { backgroundColor: theme.primary }
                  ]}>
                    {selectedSkills.includes(skill.id) && (
                      <Ionicons name="checkmark" size={16} color="#FFF" />
                    )}
                  </View>
                  <Text
                    style={[
                      styles.categoryLabel,
                      { color: theme.text },
                      selectedSkills.includes(skill.id) && { color: theme.primary, fontFamily: 'Poppins_600SemiBold' },
                    ]}
                  >
                    {skill.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
        {/* Work Experience Note */}
        <View style={[styles.section, { backgroundColor: theme.surface, shadowColor: isDark ? '#000' : '#000', shadowOpacity: isDark ? 0.3 : 0.1 }]}>
          <View style={styles.sectionHeader}>
            <Ionicons name="briefcase-outline" size={24} color={theme.primary} />
            <View style={styles.sectionTitleContainer}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Work Experience</Text>
              <Text style={[styles.sectionSubtitle, { color: theme.textSecondary }]}>
                Manage your work history
              </Text>
            </View>
          </View>
          
          <TouchableOpacity 
            style={[styles.changePhotoButton, { backgroundColor: theme.primary }]}
            onPress={() => router.push('/experience' as any)}
          >
            <Ionicons name="briefcase" size={20} color="#FFF" />
            <Text style={[styles.changePhotoText, { color: '#FFF' }]}>Manage Experience</Text>
          </TouchableOpacity>
        </View>
        {/* Save Button */}
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.saveButton, { backgroundColor: theme.primary }, saving && styles.disabledButton]}
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
            <Text style={[styles.cancelButtonText, { color: theme.textSecondary }]}>Cancel</Text>
          </TouchableOpacity>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}