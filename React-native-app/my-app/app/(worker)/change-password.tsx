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
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

export default function ChangePasswordScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      Alert.alert(t('common.error'), t('auth.fillAllFieldsError'));
      return;
    }

    if (newPassword !== confirmPassword) {
      Alert.alert(t('common.error'), t('security.newPasswordsNoMatch'));
      return;
    }

    if (newPassword.length < 8) {
      Alert.alert(t('common.error'), t('security.newPasswordMinLength'));
      return;
    }

    if (newPassword === currentPassword) {
      Alert.alert(t('common.error'), t('security.newPasswordDifferent'));
      return;
    }

    setLoading(true);
    try {
      await apiService.changePassword(currentPassword, newPassword);
      
      Alert.alert(
        'Success!',
        'Your password has been changed successfully.',
        [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
      
      // Clear form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.current_password?.[0] ||
        error.response?.data?.error ||
        error.response?.data?.message ||
        'Failed to change password. Please check your current password and try again.';
      
      Alert.alert(t('security.changePasswordFailed'), errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = () => {
    if (!newPassword) return null;
    
    let strength = 0;
    if (newPassword.length >= 8) strength++;
    if (newPassword.length >= 12) strength++;
    if (/[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)) strength++;
    if (/\d/.test(newPassword)) strength++;
    if (/[^a-zA-Z0-9]/.test(newPassword)) strength++;

    if (strength <= 2) return { text: 'Weak', color: '#ef4444' };
    if (strength <= 3) return { text: 'Medium', color: '#f59e0b' };
    return { text: 'Strong', color: '#10b981' };
  };

  const passwordStrength = getPasswordStrength();

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title="Change Password" showBack />
      
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Info Section */}
          <View style={[styles.infoCard, { backgroundColor: theme.card }]}>
            <Ionicons name="information-circle" size={24} color="#4f46e5" />
            <Text style={[styles.infoText, { color: theme.text }]}>{t('security.chooseStrongPasswordMessage')}</Text>
          </View>

          {/* Current Password */}
          <View style={styles.inputSection}>
            <Text style={[styles.label, { color: theme.text }]}>{t('security.currentPassword')}</Text>
            <View style={[styles.passwordContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <TextInput
                style={[styles.passwordInput, { color: theme.text }]}
                placeholder={t('security.enterCurrentPassword')}
                placeholderTextColor={theme.textSecondary}
                value={currentPassword}
                onChangeText={setCurrentPassword}
                secureTextEntry={!showCurrentPassword}
                autoCapitalize="none"
                autoComplete="password"
              />
              <TouchableOpacity
                style={styles.eyeButton}
                onPress={() => setShowCurrentPassword(!showCurrentPassword)}
              >
                <Ionicons
                  name={showCurrentPassword ? 'eye-off' : 'eye'}
                  size={22}
                  color={theme.textSecondary}
                />
              </TouchableOpacity>
            </View>
          </View>

          {/* New Password */}
          <View style={styles.inputSection}>
            <Text style={[styles.label, { color: theme.text }]}>{t('auth.newPassword')}</Text>
            <View style={[styles.passwordContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <TextInput
                style={[styles.passwordInput, { color: theme.text }]}
                placeholder={t('security.enterNewPassword')}
                placeholderTextColor={theme.textSecondary}
                value={newPassword}
                onChangeText={setNewPassword}
                secureTextEntry={!showNewPassword}
                autoCapitalize="none"
                autoComplete="password-new"
              />
              <TouchableOpacity
                style={styles.eyeButton}
                onPress={() => setShowNewPassword(!showNewPassword)}
              >
                <Ionicons
                  name={showNewPassword ? 'eye-off' : 'eye'}
                  size={22}
                  color={theme.textSecondary}
                />
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

          {/* Confirm Password */}
          <View style={styles.inputSection}>
            <Text style={[styles.label, { color: theme.text }]}>{t('security.confirmNewPassword')}</Text>
            <View style={[styles.passwordContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <TextInput
                style={[styles.passwordInput, { color: theme.text }]}
                placeholder={t('security.confirmNewPassword')}
                placeholderTextColor={theme.textSecondary}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showNewPassword}
                autoCapitalize="none"
                autoComplete="password-new"
              />
            </View>
            {confirmPassword && newPassword !== confirmPassword && (
              <Text style={styles.errorText}>{t('auth.passwordsNoMatch')}</Text>
            )}
          </View>

          {/* Password Requirements */}
          <View style={[styles.requirementsCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.requirementsTitle, { color: theme.text }]}>{t('auth.passwordRequirements')}</Text>
            <View style={styles.requirementsList}>
              <View style={styles.requirementItem}>
                <Ionicons
                  name={newPassword.length >= 8 ? 'checkmark-circle' : 'ellipse-outline'}
                  size={16}
                  color={newPassword.length >= 8 ? '#10b981' : theme.textSecondary}
                />
                <Text style={[styles.requirementText, { color: theme.textSecondary }]}>{t('auth.atLeast8Chars')}</Text>
              </View>
              <View style={styles.requirementItem}>
                <Ionicons
                  name={
                    /[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)
                      ? 'checkmark-circle'
                      : 'ellipse-outline'
                  }
                  size={16}
                  color={
                    /[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)
                      ? '#10b981'
                      : theme.textSecondary
                  }
                />
                <Text style={[styles.requirementText, { color: theme.textSecondary }]}>{t('auth.uppercaseLowercase')}</Text>
              </View>
              <View style={styles.requirementItem}>
                <Ionicons
                  name={/\d/.test(newPassword) ? 'checkmark-circle' : 'ellipse-outline'}
                  size={16}
                  color={/\d/.test(newPassword) ? '#10b981' : theme.textSecondary}
                />
                <Text style={[styles.requirementText, { color: theme.textSecondary }]}>{t('auth.atLeastOneNumber')}</Text>
              </View>
            </View>
          </View>

          {/* Buttons */}
          <TouchableOpacity
            style={[styles.saveButton, loading && styles.saveButtonDisabled]}
            onPress={handleChangePassword}
            disabled={loading}
          >
            {loading ? (
              <Text style={styles.saveButtonText}>{t('security.changingPassword')}</Text>
            ) : (
              <>
                <Ionicons name="shield-checkmark" size={20} color="#fff" />
                <Text style={styles.saveButtonText}>{t('security.changePassword')}</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => router.back()}
          >
            <Text style={[styles.cancelButtonText, { color: theme.textSecondary }]}>{t('common.cancel')}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#4f46e5',
  },
  infoText: {
    flex: 1,
    marginLeft: 12,
    fontSize: 14,
    lineHeight: 20,
  },
  inputSection: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: 12,
    paddingRight: 12,
  },
  passwordInput: {
    flex: 1,
    height: 52,
    paddingHorizontal: 16,
    fontSize: 16,
  },
  eyeButton: {
    padding: 8,
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
  requirementsCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  requirementsTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
  },
  requirementsList: {
    gap: 8,
  },
  requirementItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  requirementText: {
    fontSize: 13,
  },
  saveButton: {
    backgroundColor: '#4f46e5',
    height: 52,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  saveButtonDisabled: {
    backgroundColor: '#94a3b8',
    shadowOpacity: 0,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  cancelButton: {
    height: 52,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
});
