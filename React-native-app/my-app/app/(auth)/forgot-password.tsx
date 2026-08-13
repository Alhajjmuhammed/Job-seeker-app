import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

export default function ForgotPasswordScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSend = async () => {
    if (!email.trim()) {
      Alert.alert(t('common.error'), t('auth.enterEmail') || 'Please enter your email address');
      return;
    }

    setLoading(true);
    try {
      await apiService.requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.response?.data?.message || t('auth.resetFailed') || 'Could not send reset email. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },
    header: { flexDirection: 'row', alignItems: 'center', marginBottom: 32 },
    backBtn: { padding: 4, marginRight: 12 },
    headerTitle: { fontSize: 20, fontFamily: theme.fontBold, color: theme.text },
    iconWrap: {
      alignSelf: 'center',
      width: 80, height: 80, borderRadius: 40,
      backgroundColor: theme.primary + '20',
      alignItems: 'center', justifyContent: 'center',
      marginBottom: 20,
    },
    title: { fontSize: 22, fontFamily: theme.fontBold, color: theme.text, textAlign: 'center', marginBottom: 8 },
    subtitle: {
      fontSize: 14, fontFamily: theme.fontRegular, color: theme.textSecondary,
      textAlign: 'center', lineHeight: 22, marginBottom: 32,
    },
    label: { fontSize: 13, fontFamily: theme.fontSemiBold, color: theme.text, marginBottom: 6 },
    inputWrap: {
      flexDirection: 'row', alignItems: 'center',
      backgroundColor: theme.surface, borderWidth: 1.5,
      borderColor: theme.border, borderRadius: 12,
      paddingHorizontal: 14, marginBottom: 20, height: 50,
    },
    input: { flex: 1, fontSize: 15, fontFamily: theme.fontRegular, color: theme.text },
    sendBtn: {
      backgroundColor: theme.primary, borderRadius: 12,
      height: 52, alignItems: 'center', justifyContent: 'center',
    },
    sendBtnText: { fontSize: 16, fontFamily: theme.fontBold, color: '#fff' },
    backToLogin: { alignItems: 'center', marginTop: 20 },
    backToLoginText: { fontSize: 14, fontFamily: theme.fontMedium, color: theme.primary },
    successIconWrap: {
      alignSelf: 'center',
      width: 80, height: 80, borderRadius: 40,
      backgroundColor: theme.success + '20',
      alignItems: 'center', justifyContent: 'center',
      marginBottom: 20,
    },
    successTitle: { fontSize: 22, fontFamily: theme.fontBold, color: theme.text, textAlign: 'center', marginBottom: 8 },
    successText: {
      fontSize: 14, fontFamily: theme.fontRegular, color: theme.textSecondary,
      textAlign: 'center', lineHeight: 22, marginBottom: 32,
    },
  });

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        <View style={s.header}>
          <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={22} color={theme.text} />
          </TouchableOpacity>
          <Text style={s.headerTitle}>{t('auth.resetPassword') || 'Reset Password'}</Text>
        </View>

        {!sent ? (
          <>
            <View style={s.iconWrap}>
              <Ionicons name="lock-open-outline" size={36} color={theme.primary} />
            </View>
            <Text style={s.title}>{t('auth.forgotPassword') || 'Forgot Password?'}</Text>
            <Text style={s.subtitle}>
              {t('auth.resetInstructions') ||
                "Enter your email address and we'll send you a link to reset your password."}
            </Text>

            <Text style={s.label}>{t('auth.email') || 'Email address'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="mail-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder={t('auth.emailPlaceholder') || 'Enter your email'}
                placeholderTextColor={theme.textTertiary}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                autoFocus
              />
            </View>

            <TouchableOpacity style={s.sendBtn} onPress={handleSend} disabled={loading}>
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={s.sendBtnText}>{t('auth.sendResetLink') || 'Send Reset Link'}</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity style={s.backToLogin} onPress={() => router.replace('/(auth)/login')}>
              <Text style={s.backToLoginText}>{t('auth.backToLogin') || 'Back to Login'}</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <View style={s.successIconWrap}>
              <Ionicons name="checkmark-circle" size={40} color={theme.success} />
            </View>
            <Text style={s.successTitle}>{t('auth.checkYourEmail') || 'Check your email'}</Text>
            <Text style={s.successText}>
              {t('auth.resetLinkSent') ||
                `We've sent a password reset link to ${email}. Please check your inbox.`}
            </Text>
            <TouchableOpacity style={s.sendBtn} onPress={() => router.replace('/(auth)/login')}>
              <Text style={s.sendBtnText}>{t('auth.backToLogin') || 'Back to Login'}</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
