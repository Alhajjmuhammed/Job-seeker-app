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
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

const TEAL = '#0D6E68';

export default function LoginScreen() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const { theme, isDark } = useTheme();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [emailFocused, setEmailFocused] = useState(false);
  const [passFocused, setPassFocused] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert(t('error'), t('fillAllFields') || 'Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
    } catch (error: any) {
      Alert.alert(
        t('error'),
        error.message || t('loginFailed') || 'Login failed. Please check your credentials.',
      );
    } finally {
      setLoading(false);
    }
  };

  const bg = isDark ? '#0a1a18' : '#f0faf9';
  const cardBg = isDark ? '#112220' : '#ffffff';
  const textPrimary = isDark ? '#ffffff' : '#0d1f1e';
  const textSec = isDark ? '#8aa8a6' : '#6b8f8d';
  const inputBg = isDark ? '#1a2e2c' : '#f7fdfb';
  const borderNormal = isDark ? '#1e3432' : '#e0f0ee';

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: bg }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style={isDark ? 'light' : 'dark'} />

      {/* Decorative background circles */}
      <View style={styles.circle1} />
      <View style={styles.circle2} />
      <View style={styles.circle3} />

      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Logo section */}
        <View style={styles.logoSection}>
          <Image
            source={require('../../assets/images/logo.png')}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={[styles.appName, { color: isDark ? '#fff' : TEAL }]}>Worker Connect</Text>
        </View>

        {/* Form card */}
        <View style={[styles.card, { backgroundColor: cardBg }]}>
          <Text style={[styles.heading, { color: textPrimary }]}>
            {t('welcomeBack') || 'Welcome back!'}
          </Text>
          <Text style={[styles.subheading, { color: textSec }]}>
            {t('loginSubtitle') || 'Sign in to your account to continue'}
          </Text>

          {/* Email */}
          <View
            style={[
              styles.fieldWrap,
              { backgroundColor: inputBg, borderColor: emailFocused ? TEAL : borderNormal },
            ]}
          >
            <View
              style={[
                styles.iconBadge,
                { backgroundColor: emailFocused ? TEAL : (isDark ? '#1e3432' : '#e8f7f5') },
              ]}
            >
              <Ionicons name="mail" size={16} color={emailFocused ? '#fff' : (isDark ? '#8aa8a6' : TEAL)} />
            </View>
            <TextInput
              style={[styles.fieldInput, { color: textPrimary }]}
              placeholder={t('emailAddress') || 'Email address'}
              placeholderTextColor={textSec}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              onFocus={() => setEmailFocused(true)}
              onBlur={() => setEmailFocused(false)}
            />
          </View>

          {/* Password */}
          <View
            style={[
              styles.fieldWrap,
              { backgroundColor: inputBg, borderColor: passFocused ? TEAL : borderNormal },
            ]}
          >
            <View
              style={[
                styles.iconBadge,
                { backgroundColor: passFocused ? TEAL : (isDark ? '#1e3432' : '#e8f7f5') },
              ]}
            >
              <Ionicons name="lock-closed" size={16} color={passFocused ? '#fff' : (isDark ? '#8aa8a6' : TEAL)} />
            </View>
            <TextInput
              style={[styles.fieldInput, { color: textPrimary }]}
              placeholder={t('password') || 'Password'}
              placeholderTextColor={textSec}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              onFocus={() => setPassFocused(true)}
              onBlur={() => setPassFocused(false)}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
              <Ionicons name={showPassword ? 'eye-off' : 'eye'} size={18} color={textSec} />
            </TouchableOpacity>
          </View>

          {/* Forgot password */}
          <TouchableOpacity
            style={styles.forgotRow}
            onPress={() => router.push('/(auth)/forgot-password')}
          >
            <Text style={[styles.forgotText, { color: TEAL }]}>
              {t('forgotPassword') || 'Forgot password?'}
            </Text>
          </TouchableOpacity>

          {/* Sign In button */}
          <TouchableOpacity
            style={[styles.signInBtn, loading && { opacity: 0.75 }]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Text style={styles.signInText}>{t('signIn') || 'Sign In'}</Text>
                <View style={styles.arrowCircle}>
                  <Ionicons name="arrow-forward" size={16} color={TEAL} />
                </View>
              </>
            )}
          </TouchableOpacity>

          {/* Register */}
          <View style={styles.registerRow}>
            <Text style={[styles.registerLabel, { color: textSec }]}>
              {t('noAccount') || "Don't have an account?"}
            </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/register')}>
              <Text style={[styles.registerLink, { color: TEAL }]}>
                {'  '}{t('createAccount') || 'Create one'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  circle1: {
    position: 'absolute',
    width: 360,
    height: 360,
    borderRadius: 180,
    backgroundColor: 'rgba(13,110,104,0.13)',
    top: -140,
    right: -110,
  },
  circle2: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: 'rgba(13,110,104,0.07)',
    bottom: 40,
    left: -70,
  },
  circle3: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: 'rgba(13,110,104,0.09)',
    top: 160,
    left: -40,
  },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 72,
    paddingBottom: 40,
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 36,
  },


  logo: { width: 130, height: 130, borderRadius: 65, marginBottom: 16 },
  appName: {
    fontSize: 24,
    fontFamily: 'Poppins_700Bold',
    letterSpacing: 0.2,
  },
  tagline: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    marginTop: 3,
  },
  card: {
    borderRadius: 28,
    paddingHorizontal: 24,
    paddingVertical: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 24,
    elevation: 8,
  },
  heading: {
    fontSize: 26,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 6,
  },
  subheading: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
    marginBottom: 28,
  },
  fieldWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 14,
    gap: 10,
  },
  iconBadge: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fieldInput: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    paddingVertical: 2,
  },
  eyeBtn: { padding: 4 },
  forgotRow: {
    alignSelf: 'flex-end',
    marginBottom: 26,
    marginTop: 2,
  },
  forgotText: {
    fontSize: 13,
    fontFamily: 'Poppins_600SemiBold',
  },
  signInBtn: {
    backgroundColor: TEAL,
    borderRadius: 16,
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 26,
    paddingHorizontal: 20,
    shadowColor: TEAL,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.42,
    shadowRadius: 14,
    elevation: 7,
  },
  signInText: {
    flex: 1,
    textAlign: 'center',
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
    color: '#fff',
    letterSpacing: 0.3,
    marginLeft: 34,
  },
  arrowCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  registerRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  registerLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  registerLink: {
    fontSize: 14,
    fontFamily: 'Poppins_700Bold',
  },
});
