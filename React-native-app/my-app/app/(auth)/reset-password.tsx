import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ScrollView,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useLocalSearchParams } from 'expo-router';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

export default function ResetPasswordScreen() {
  const { t } = useTranslation();
  const { uid, token } = useLocalSearchParams<{ uid?: string; token?: string }>();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (!uid || !token) {
      Alert.alert(
        'Invalid Link',
        'The password reset link is invalid or expired. Please request a new one.',
        [{ text: 'OK', onPress: () => router.replace('/(auth)/forgot-password') }]
      );
    }
  }, [uid, token]);

  const handleResetPassword = async () => {
    if (!password || !confirmPassword) {
      Alert.alert(t('common.error'), t('auth.fillAllFieldsError'));
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert(t('common.error'), t('auth.passwordsNoMatch'));
      return;
    }

    if (password.length < 8) {
      Alert.alert(t('common.error'), t('auth.passwordMinLength'));
      return;
    }

    if (!uid || !token) {
      Alert.alert(t('common.error'), t('auth.invalidResetToken'));
      return;
    }

    setLoading(true);
    try {
      // Combine uid and token as expected by the backend
      const resetToken = `${uid}:${token}`;
      await apiService.confirmPasswordReset(resetToken, password);
      
      Alert.alert(
        'Success!',
        'Your password has been reset successfully. You can now login with your new password.',
        [
          {
            text: 'Go to Login',
            onPress: () => router.replace('/(auth)/login'),
          },
        ]
      );
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error ||
        error.response?.data?.message ||
        'Failed to reset password. The link may be expired or invalid.';
      
      Alert.alert(t('auth.resetFailed'), errorMessage, [
        {
          text: 'Request New Link',
          onPress: () => router.replace('/(auth)/forgot-password'),
        },
        { text: 'Cancel', style: 'cancel' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = () => {
    if (!password) return null;
    
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    if (strength <= 2) return { text: 'Weak', color: '#ef4444' };
    if (strength <= 3) return { text: 'Medium', color: '#f59e0b' };
    return { text: 'Strong', color: '#10b981' };
  };

  const passwordStrength = getPasswordStrength();

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
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>🔒</Text>
            </View>
            <Text style={styles.title}>{t('auth.resetPassword')}</Text>
            <Text style={styles.subtitle}>{t('auth.chooseStrongPassword')}</Text>
          </View>

          {/* Form */}
          <View style={styles.formContainer}>
            <View style={styles.inputContainer}>
              <Text style={styles.label}>{t('auth.newPassword')}</Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder={t('security.enterNewPassword')}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  autoComplete="password-new"
                />
                <TouchableOpacity
                  style={styles.eyeButton}
                  onPress={() => setShowPassword(!showPassword)}
                >
                  <Text style={styles.eyeIcon}>{showPassword ? '👁️' : '👁️‍🗨️'}</Text>
                </TouchableOpacity>
              </View>
              {passwordStrength && (
                <View style={styles.strengthContainer}>
                  <Text style={[styles.strengthText, { color: passwordStrength.color }]}>
                    Password Strength: {passwordStrength.text}
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>{t('security.confirmNewPassword')}</Text>
              <TextInput
                style={styles.input}
                placeholder={t('auth.confirmYourPassword')}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoComplete="password-new"
              />
              {confirmPassword && password !== confirmPassword && (
                <Text style={styles.errorText}>{t('auth.passwordsNoMatch')}</Text>
              )}
            </View>

            <View style={styles.requirementsContainer}>
              <Text style={styles.requirementsTitle}>{t('auth.passwordRequirements')}</Text>
              <Text style={styles.requirementItem}>
                {password.length >= 8 ? '✅' : '⭕'} At least 8 characters
              </Text>
              <Text style={styles.requirementItem}>
                {/[a-z]/.test(password) && /[A-Z]/.test(password) ? '✅' : '⭕'}{' '}
                Uppercase and lowercase letters
              </Text>
              <Text style={styles.requirementItem}>
                {/\d/.test(password) ? '✅' : '⭕'} At least one number
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.resetButton, loading && styles.resetButtonDisabled]}
              onPress={handleResetPassword}
              disabled={loading}
            >
              <Text style={styles.resetButtonText}>
                {loading ? 'Resetting...' : 'Reset Password'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.replace('/(auth)/login')}
            >
              <Text style={styles.backButtonText}>{t('auth.backToLogin')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#eef2ff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  icon: {
    fontSize: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  formContainer: {
    marginBottom: 20,
  },
  inputContainer: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 8,
  },
  input: {
    height: 52,
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    backgroundColor: '#fff',
    color: '#0f172a',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  passwordInput: {
    flex: 1,
    height: 52,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#0f172a',
  },
  eyeButton: {
    padding: 12,
  },
  eyeIcon: {
    fontSize: 20,
  },
  strengthContainer: {
    marginTop: 8,
  },
  strengthText: {
    fontSize: 12,
    fontWeight: '600',
  },
  errorText: {
    fontSize: 12,
    color: '#ef4444',
    marginTop: 4,
  },
  requirementsContainer: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  requirementsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 8,
  },
  requirementItem: {
    fontSize: 13,
    color: '#64748b',
    marginBottom: 4,
  },
  resetButton: {
    height: 52,
    backgroundColor: '#4f46e5',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  resetButtonDisabled: {
    backgroundColor: '#94a3b8',
    shadowOpacity: 0,
  },
  resetButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  backButton: {
    height: 52,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backButtonText: {
    fontSize: 14,
    color: '#4f46e5',
    fontWeight: '600',
  },
});
