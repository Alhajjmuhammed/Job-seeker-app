/**
 * "Complete your profile" banner on the worker dashboard.
 *
 * The full Profile Setup screen is only for workers with no National ID yet
 * (login sends them there). Everyone else lands on the dashboard and sees this
 * banner until the profile reaches `banner_until` percent (70) - then it goes away.
 */
import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../contexts/ThemeContext';
import apiService from '../services/api';

type Missing = 'id' | 'trades' | 'city' | 'bio' | 'documents';

export default function ProfileCompletionBanner() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [pct, setPct] = useState<number | null>(null);
  const [until, setUntil] = useState(70);
  const [missing, setMissing] = useState<Missing[]>([]);

  // reload every time the dashboard comes back, so it updates after editing the profile
  useFocusEffect(
    useCallback(() => {
      let alive = true;
      apiService.getProfileCompletion()
        .then((d: any) => {
          if (!alive) return;
          setPct(typeof d?.profile_completion_percentage === 'number' ? d.profile_completion_percentage : null);
          if (typeof d?.banner_until === 'number') setUntil(d.banner_until);
          setMissing(Array.isArray(d?.missing) ? d.missing : []);
        })
        .catch(() => { if (alive) setPct(null); });  // no banner rather than a wrong one
      return () => { alive = false; };
    }, [])
  );

  if (pct === null || pct >= until) {
    return null;
  }

  const go = () => {
    if (missing.includes('id') || (missing[0] === 'documents')) {
      router.push('/(worker)/documents' as any);
    } else {
      router.push('/(worker)/profile-edit' as any);
    }
  };

  return (
    <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.primary }]}>
      <View style={styles.row}>
        <Ionicons name="person-circle-outline" size={22} color={theme.primary} />
        <Text style={[styles.title, { color: theme.text }]}>
          {t('dashboard.completion.title', { pct })}
        </Text>
      </View>
      <View style={[styles.track, { backgroundColor: theme.border }]}>
        <View style={[styles.fill, { width: `${Math.max(5, Math.min(pct, 100))}%`, backgroundColor: theme.primary }]} />
      </View>
      {missing.length > 0 && (
        <Text style={[styles.hint, { color: theme.textSecondary }]}>
          {t('dashboard.completion.stillNeeded')}{' '}
          {missing.slice(0, 3).map(m => t(`dashboard.completion.missing.${m}`)).join(', ')}
        </Text>
      )}
      <TouchableOpacity onPress={go} style={[styles.button, { backgroundColor: theme.primary }]}
        accessibilityRole="button">
        <Text style={styles.buttonText}>{t('dashboard.completion.cta')}</Text>
        <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 16, borderRadius: 12, borderWidth: 1.5, padding: 14, gap: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { flex: 1, fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  track: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },
  hint: { fontSize: 13, fontFamily: 'Poppins_400Regular', lineHeight: 18 },
  button: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderRadius: 10,
    paddingVertical: 10 },
  buttonText: { color: '#FFFFFF', fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
});
