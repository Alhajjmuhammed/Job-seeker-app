import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Link } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

type UserType = 'worker' | 'client';
type WorkerType = 'professional' | 'non-academic';

export default function RegisterScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [userType, setUserType] = useState<UserType>('worker');
  const [workerType, setWorkerType] = useState<WorkerType>('non-academic');
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    agentCode: '',
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleRegister = async () => {
    if (!formData.firstName || !formData.lastName || !formData.email || !formData.password) {
      Alert.alert(t('common.error'), t('auth.fillAllFields'));
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      Alert.alert(t('common.error'), t('auth.passwordsNoMatch'));
      return;
    }

    setLoading(true);
    try {
      await register({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        password: formData.password,
        userType: userType,
        workerType: userType === 'worker' ? workerType : undefined,
        agentCode: userType === 'worker' && formData.agentCode.trim() ? formData.agentCode.trim().toUpperCase() : undefined,
      });
      // Navigation is handled by AuthContext based on user type
    } catch (error: any) {
      Alert.alert(t('auth.registrationFailed'), error.message || 'Please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <StatusBar style="dark" />
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Image
            source={require('@/assets/images/logo.png')}
            style={styles.logoImage}
            resizeMode="cover"
          />
          <Text style={styles.title}>{t('auth.createAccount')}</Text>
          <Text style={styles.subtitle}>{t('auth.joinToday')}</Text>
        </View>

        {/* User Type Selection */}
        <View style={styles.userTypeContainer}>
          <Text style={styles.label}>{t('auth.iWantTo')}</Text>
          <View style={styles.userTypeButtons}>
            <TouchableOpacity
              style={[
                styles.userTypeButton,
                userType === 'worker' && styles.userTypeButtonActive,
              ]}
              onPress={() => setUserType('worker')}
            >
              <Text
                style={[
                  styles.userTypeButtonText,
                  userType === 'worker' && styles.userTypeButtonTextActive,
                ]}
              >{t('auth.findWork')}</Text>
              <Text
                style={[
                  styles.userTypeSubtext,
                  userType === 'worker' && styles.userTypeSubtextActive,
                ]}
              >{t('auth.imWorker')}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.userTypeButton,
                userType === 'client' && styles.userTypeButtonActive,
              ]}
              onPress={() => setUserType('client')}
            >
              <Text
                style={[
                  styles.userTypeButtonText,
                  userType === 'client' && styles.userTypeButtonTextActive,
                ]}
              >{t('auth.hireWorkers')}</Text>
              <Text
                style={[
                  styles.userTypeSubtext,
                  userType === 'client' && styles.userTypeSubtextActive,
                ]}
              >{t('auth.iNeedHelp')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Worker Type Selection (only for workers) */}
        {userType === 'worker' && (
          <View style={styles.workerTypeContainer}>
            <Text style={styles.label}>{t('auth.workerType')}</Text>
            <View style={styles.workerTypeButtons}>
              <TouchableOpacity
                style={[
                  styles.workerTypeButton,
                  workerType === 'professional' && styles.workerTypeButtonActive,
                ]}
                onPress={() => setWorkerType('professional')}
              >
                <Text style={styles.workerTypeIcon}>🎓</Text>
                <Text
                  style={[
                    styles.workerTypeButtonText,
                    workerType === 'professional' && styles.workerTypeButtonTextActive,
                  ]}
                >{t('auth.professional')}</Text>
                <Text style={styles.workerTypeDesc}>{t('auth.universityDegree')}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.workerTypeButton,
                  workerType === 'non-academic' && styles.workerTypeButtonActive,
                ]}
                onPress={() => setWorkerType('non-academic')}
              >
                <Text style={styles.workerTypeIcon}>🔧</Text>
                <Text
                  style={[
                    styles.workerTypeButtonText,
                    workerType === 'non-academic' && styles.workerTypeButtonTextActive,
                  ]}
                >{t('auth.nonAcademic')}</Text>
                <Text style={styles.workerTypeDesc}>{t('auth.skilledWorker')}</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* 
        {/* Form Fields */}
        <View style={styles.formContainer}>
          <View style={styles.row}>
            <View style={styles.halfInput}>
              <Text style={styles.label}>{t('auth.firstName')}</Text>
              <TextInput
                style={styles.input}
                placeholder="John"
                value={formData.firstName}
                onChangeText={(text) => setFormData({ ...formData, firstName: text })}
              />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.label}>{t('auth.lastName')}</Text>
              <TextInput
                style={styles.input}
                placeholder="Doe"
                value={formData.lastName}
                onChangeText={(text) => setFormData({ ...formData, lastName: text })}
              />
            </View>
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>{t('auth.email')}</Text>
            <TextInput
              style={styles.input}
              placeholder="your@email.com"
              value={formData.email}
              onChangeText={(text) => setFormData({ ...formData, email: text })}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>{t('client.phoneNumber')}</Text>
            <TextInput
              style={styles.input}
              placeholder="+249 123 456 789"
              value={formData.phone}
              onChangeText={(text) => setFormData({ ...formData, phone: text })}
              keyboardType="phone-pad"
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>{t('auth.password')}</Text>
            <TextInput
              style={styles.input}
              placeholder="Minimum 8 characters"
              value={formData.password}
              onChangeText={(text) => setFormData({ ...formData, password: text })}
              secureTextEntry
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>{t('auth.confirmPassword')}</Text>
            <TextInput
              style={styles.input}
              placeholder="Re-enter password"
              value={formData.confirmPassword}
              onChangeText={(text) => setFormData({ ...formData, confirmPassword: text })}
              secureTextEntry
            />
          </View>

          {userType === 'worker' && (
            <View style={styles.inputContainer}>
              <Text style={styles.label}>Agent Code <Text style={{ color: '#9CA3AF', fontFamily: 'Poppins_400Regular' }}>{t('auth.optional')}</Text></Text>
              <TextInput
                style={styles.input}
                placeholder={t('auth.enterAgentCode')}
                value={formData.agentCode}
                onChangeText={(text) => setFormData({ ...formData, agentCode: text.toUpperCase() })}
                autoCapitalize="characters"
                maxLength={10}
              />
            </View>
          )}

          <TouchableOpacity
            style={[styles.registerButton, loading && styles.registerButtonDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            <Text style={styles.registerButtonText}>
              {loading ? 'Creating Account...' : 'Create Account'}
            </Text>
          </TouchableOpacity>

          <View style={styles.termsContainer}>
            <Text style={styles.termsText}>
              By signing up, you agree to our{' '}
              <Text style={styles.termsLink}>{t('terms.termsOfService')}</Text> and{' '}
              <Text style={styles.termsLink}>{t('auth.privacyPolicy')}</Text>
            </Text>
          </View>

          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>{t('auth.haveAccount')}</Text>
            <Link href="/(auth)/login" asChild>
              <TouchableOpacity>
                <Text style={styles.loginLink}>{t('auth.signIn')}</Text>
              </TouchableOpacity>
            </Link>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoImage: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#FFFFFF',
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontFamily: 'Poppins_700Bold',
    color: '#1F2937',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
  },
  userTypeContainer: {
    marginBottom: 32,
  },
  label: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    color: '#374151',
    marginBottom: 8,
  },
  userTypeButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  userTypeButton: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#E5E7EB',
    backgroundColor: '#F9FAFB',
    alignItems: 'center',
  },
  userTypeButtonActive: {
    borderColor: '#0F766E',
    backgroundColor: '#ECFDF5',
  },
  userTypeButtonText: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    color: '#6B7280',
    marginBottom: 4,
  },
  userTypeButtonTextActive: {
    color: '#0F766E',
  },
  userTypeSubtext: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#9CA3AF',
  },
  userTypeSubtextActive: {
    color: '#0F766E',
  },
  formContainer: {
    width: '100%',
  },
  row: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  halfInput: {
    flex: 1,
  },
  inputContainer: {
    marginBottom: 20,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
    backgroundColor: '#F9FAFB',
  },
  registerButton: {
    height: 54,
    backgroundColor: '#0F766E',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 16,
  },
  registerButtonDisabled: {
    opacity: 0.6,
  },
  registerButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  termsContainer: {
    marginBottom: 24,
  },
  termsText: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 18,
  },
  termsLink: {
    color: '#0F766E',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  loginText: {
    color: '#6B7280',
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  loginLink: {
    color: '#0F766E',
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
  },
  workerTypeContainer: {
    marginBottom: 24,
  },
  workerTypeButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  workerTypeButton: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  workerTypeButtonActive: {
    backgroundColor: '#D1FAE5',
    borderColor: '#0F766E',
  },
  workerTypeIcon: {
    fontSize: 32,
    fontFamily: 'Poppins_400Regular',
    marginBottom: 8,
  },
  workerTypeButtonText: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    color: '#374151',
    marginBottom: 4,
  },
  workerTypeButtonTextActive: {
    color: '#0F766E',
  },
  workerTypeDesc: {
    fontSize: 11,
    fontFamily: 'Poppins_400Regular',
    color: '#6B7280',
    textAlign: 'center',
  },
});
