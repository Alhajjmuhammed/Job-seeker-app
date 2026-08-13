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
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useTranslation } from 'react-i18next';

type UserType = 'worker' | 'client';
type WorkerType = 'professional' | 'non-academic';

export default function RegisterScreen() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const { theme, isDark } = useTheme();

  const [step, setStep] = useState<1 | 2>(1);
  const [userType, setUserType] = useState<UserType>('client');
  const [workerType, setWorkerType] = useState<WorkerType>('non-academic');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agentCode, setAgentCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const goToStep2 = () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !phone.trim()) {
      Alert.alert(t('common.error'), t('auth.fillAllFields') || 'Please fill in all fields');
      return;
    }
    setStep(2);
  };

  const handleRegister = async () => {
    if (!password.trim() || !confirmPassword.trim()) {
      Alert.alert(t('common.error'), t('auth.fillAllFields') || 'Please fill in all fields');
      return;
    }
    if (password !== confirmPassword) {
      Alert.alert(t('common.error'), t('auth.passwordMismatch') || 'Passwords do not match');
      return;
    }
    if (password.length < 8) {
      Alert.alert(t('common.error'), t('auth.passwordTooShort') || 'Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await register({
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim(),
        password,
        userType,
        workerType: userType === 'worker' ? workerType : undefined,
        agentCode: agentCode.trim() || undefined,
      });
    } catch (error: any) {
      Alert.alert(
        t('common.error'),
        error.message || t('auth.registerFailed') || 'Registration failed. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.background },
    scroll: { flexGrow: 1, padding: 24 },
    header: { flexDirection: 'row', alignItems: 'center', marginBottom: 28, marginTop: 8 },
    backBtn: { padding: 4, marginRight: 12 },
    headerTitle: { fontSize: 20, fontFamily: theme.fontBold, color: theme.text },
    stepRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 24 },
    stepDot: {
      width: 28, height: 28, borderRadius: 14,
      alignItems: 'center', justifyContent: 'center',
    },
    stepDotText: { fontSize: 12, fontFamily: theme.fontBold, color: '#fff' },
    stepLine: { flex: 1, height: 2, marginHorizontal: 8 },
    sectionTitle: { fontSize: 16, fontFamily: theme.fontBold, color: theme.text, marginBottom: 4 },
    sectionSub: { fontSize: 13, fontFamily: theme.fontRegular, color: theme.textSecondary, marginBottom: 20 },
    typeRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
    typeCard: {
      flex: 1, borderRadius: 14, padding: 16,
      alignItems: 'center', borderWidth: 2,
    },
    typeIcon: { marginBottom: 8 },
    typeLabel: { fontSize: 14, fontFamily: theme.fontSemiBold },
    typeDesc: { fontSize: 11, fontFamily: theme.fontRegular, textAlign: 'center', marginTop: 4 },
    label: { fontSize: 13, fontFamily: theme.fontSemiBold, color: theme.text, marginBottom: 6 },
    inputWrap: {
      flexDirection: 'row', alignItems: 'center',
      backgroundColor: theme.background, borderWidth: 1.5,
      borderColor: theme.border, borderRadius: 12,
      paddingHorizontal: 14, marginBottom: 16, height: 50,
    },
    input: { flex: 1, fontSize: 15, fontFamily: theme.fontRegular, color: theme.text },
    eyeBtn: { padding: 4 },
    workerTypeRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
    workerTypeBtn: {
      flex: 1, borderRadius: 10, padding: 12,
      alignItems: 'center', borderWidth: 1.5,
    },
    workerTypeBtnText: { fontSize: 13, fontFamily: theme.fontSemiBold },
    optionalLabel: { fontSize: 12, fontFamily: theme.fontRegular, color: theme.textSecondary, marginBottom: 6 },
    primaryBtn: {
      backgroundColor: theme.primary, borderRadius: 12,
      height: 52, alignItems: 'center', justifyContent: 'center', marginTop: 8,
    },
    primaryBtnText: { fontSize: 16, fontFamily: theme.fontBold, color: '#fff' },
    loginRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 20 },
    loginText: { fontSize: 13, fontFamily: theme.fontRegular, color: theme.textSecondary },
    loginLink: { fontSize: 13, fontFamily: theme.fontSemiBold, color: theme.primary, marginLeft: 4 },
  });

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        {/* Header */}
        <View style={s.header}>
          <TouchableOpacity
            style={s.backBtn}
            onPress={() => (step === 2 ? setStep(1) : router.back())}
          >
            <Ionicons name="arrow-back" size={22} color={theme.text} />
          </TouchableOpacity>
          <Text style={s.headerTitle}>{'Create Account'}</Text>
        </View>

        {/* Step indicator */}
        <View style={s.stepRow}>
          <View style={[s.stepDot, { backgroundColor: theme.primary }]}>
            <Text style={s.stepDotText}>1</Text>
          </View>
          <View style={[s.stepLine, { backgroundColor: step === 2 ? theme.primary : theme.border }]} />
          <View style={[s.stepDot, { backgroundColor: step === 2 ? theme.primary : theme.border }]}>
            <Text style={[s.stepDotText, { color: step === 2 ? '#fff' : theme.textSecondary }]}>2</Text>
          </View>
        </View>

        {step === 1 ? (
          <>
            <Text style={s.sectionTitle}>{'Who are you?'}</Text>
            <Text style={s.sectionSub}>{'Choose how you want to use the app'}</Text>

            {/* User type selection */}
            <View style={s.typeRow}>
              {(['client', 'worker'] as UserType[]).map((type) => (
                <TouchableOpacity
                  key={type}
                  style={[
                    s.typeCard,
                    {
                      borderColor: userType === type ? theme.primary : theme.border,
                      backgroundColor: userType === type ? theme.primary + '15' : theme.surface,
                    },
                  ]}
                  onPress={() => setUserType(type)}
                >
                  <Ionicons
                    name={type === 'client' ? 'person' : 'briefcase'}
                    size={28}
                    color={userType === type ? theme.primary : theme.textSecondary}
                    style={s.typeIcon}
                  />
                  <Text style={[s.typeLabel, { color: userType === type ? theme.primary : theme.text }]}>
                    {type === 'client' ? 'Client' : 'Worker'}
                  </Text>
                  <Text style={[s.typeDesc, { color: theme.textSecondary }]}>
                    {type === 'client' ? 'I need services' : 'I provide services'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Personal info */}
            <Text style={s.label}>{'First Name'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="person-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Enter your first name"
                placeholderTextColor={theme.textTertiary}
                value={firstName}
                onChangeText={setFirstName}
                autoCapitalize="words"
              />
            </View>

            <Text style={s.label}>{'Last Name'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="person-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Enter your last name"
                placeholderTextColor={theme.textTertiary}
                value={lastName}
                onChangeText={setLastName}
                autoCapitalize="words"
              />
            </View>

            <Text style={s.label}>{'Email'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="mail-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Enter your email"
                placeholderTextColor={theme.textTertiary}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <Text style={s.label}>{'Phone Number'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="call-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="+255 700 000 000"
                placeholderTextColor={theme.textTertiary}
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
              />
            </View>

            <TouchableOpacity style={s.primaryBtn} onPress={goToStep2}>
              <Text style={s.primaryBtnText}>{'Next'}</Text>
            </TouchableOpacity>

            <View style={s.loginRow}>
              <Text style={s.loginText}>{'Already have an account?'}</Text>
              <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
                <Text style={s.loginLink}>{'Sign In'}</Text>
              </TouchableOpacity>
            </View>
          </>
        ) : (
          <>
            <Text style={s.sectionTitle}>{'Secure your account'}</Text>
            <Text style={s.sectionSub}>{'Create a strong password'}</Text>

            {/* Worker type if worker */}
            {userType === 'worker' && (
              <>
                <Text style={s.label}>{'Worker Type'}</Text>
                <View style={s.workerTypeRow}>
                  {(['professional', 'non-academic'] as WorkerType[]).map((wt) => (
                    <TouchableOpacity
                      key={wt}
                      style={[
                        s.workerTypeBtn,
                        {
                          borderColor: workerType === wt ? theme.primary : theme.border,
                          backgroundColor: workerType === wt ? theme.primary + '15' : theme.surface,
                        },
                      ]}
                      onPress={() => setWorkerType(wt)}
                    >
                      <Text style={[s.workerTypeBtnText, { color: workerType === wt ? theme.primary : theme.text }]}>
                        {wt === 'professional' ? 'Professional' : 'Non-Academic'}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}

            <Text style={s.label}>{'Password'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="lock-closed-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Min. 8 characters"
                placeholderTextColor={theme.textTertiary}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity style={s.eyeBtn} onPress={() => setShowPassword(!showPassword)}>
                <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={18} color={theme.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={s.label}>{'Confirm Password'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="lock-closed-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Re-enter your password"
                placeholderTextColor={theme.textTertiary}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showConfirm}
                autoCapitalize="none"
              />
              <TouchableOpacity style={s.eyeBtn} onPress={() => setShowConfirm(!showConfirm)}>
                <Ionicons name={showConfirm ? 'eye-off-outline' : 'eye-outline'} size={18} color={theme.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={s.optionalLabel}>{'Agent Code (optional)'}</Text>
            <View style={s.inputWrap}>
              <Ionicons name="people-outline" size={18} color={theme.textSecondary} style={{ marginRight: 8 }} />
              <TextInput
                style={s.input}
                placeholder="Enter agent code if you have one"
                placeholderTextColor={theme.textTertiary}
                value={agentCode}
                onChangeText={setAgentCode}
                autoCapitalize="characters"
              />
            </View>

            <TouchableOpacity style={s.primaryBtn} onPress={handleRegister} disabled={loading}>
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={s.primaryBtnText}>{'Create Account'}</Text>
              )}
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
