/**
 * The worker's own skills (ones not in the category lists), on profile edit.
 * Backend: GET/POST /api/workers/custom-skills/, DELETE .../<id>/ - the same
 * rules as the website's "Add custom skill" (workers/custom_skills.py).
 * Saved straight away; it doesn't wait for the profile's Save button.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../contexts/ThemeContext';
import apiService from '../services/api';
import { Btn, Field, apiError } from './vacancies/ui';

interface CustomSkill { id: number; name: string; years_of_experience: number; is_verified: boolean; description: string }

export default function CustomSkills() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [skills, setSkills] = useState<CustomSkill[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [years, setYears] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const data = await apiService.getCustomSkills();
      setSkills(data?.results || []);
    } catch {
      // an older server has no such endpoint: just show the add form
    }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!name.trim()) { setError(t('customSkills.nameRequired')); return; }
    setBusy(true);
    try {
      await apiService.addCustomSkill({
        name: name.trim(), description: description.trim(), years_of_experience: parseInt(years, 10) || 0,
      });
      setName(''); setYears(''); setDescription(''); setError(''); setOpen(false);
      Alert.alert(t('common.success'), t('customSkills.added'));
      load();
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('customSkills.failed')));
    } finally {
      setBusy(false);
    }
  };

  const remove = (s: CustomSkill) => Alert.alert(t('customSkills.remove'), `${t('customSkills.removeConfirm')}\n\n${s.name}`, [
    { text: t('common.cancel'), style: 'cancel' },
    {
      text: t('customSkills.remove'), style: 'destructive', onPress: async () => {
        try { await apiService.deleteCustomSkill(s.id); load(); } catch (e: any) {
          Alert.alert(t('common.error'), apiError(e, t('customSkills.failed')));
        }
      },
    },
  ]);

  return (
    <View>
      <View style={st.header}>
        <Ionicons name="add-circle-outline" size={24} color={theme.primary} />
        <View style={{ flex: 1 }}>
          <Text style={[st.title, { color: theme.text }]}>{t('customSkills.title')}</Text>
          <Text style={[st.sub, { color: theme.textSecondary }]}>{t('customSkills.subtitle')}</Text>
        </View>
      </View>

      {skills.length === 0 && !open && <Text style={[st.sub, { color: theme.textSecondary, marginBottom: 10 }]}>{t('customSkills.none')}</Text>}
      {skills.map(s => (
        <View key={s.id} style={[st.item, { borderColor: theme.border }]}>
          <View style={{ flex: 1 }}>
            <Text style={[st.name, { color: theme.text }]}>{s.name}</Text>
            <Text style={[st.sub, { color: s.is_verified ? theme.primary : theme.textSecondary }]}>
              {s.is_verified ? t('customSkills.verified') : t('customSkills.notVerified')}
              {s.years_of_experience ? ` · ${t('customSkills.years')}: ${s.years_of_experience}` : ''}
            </Text>
          </View>
          <TouchableOpacity onPress={() => remove(s)} accessibilityLabel={t('customSkills.remove')} hitSlop={10}>
            <Ionicons name="trash-outline" size={20} color={theme.error} />
          </TouchableOpacity>
        </View>
      ))}

      {open ? (
        <View style={{ marginTop: 8 }}>
          <Field label={t('customSkills.name')} placeholder={t('customSkills.namePlaceholder')} value={name}
            onChangeText={(v) => { setName(v); setError(''); }} maxLength={200} error={error} />
          <Field label={t('customSkills.years')} value={years} onChangeText={(v) => setYears(v.replace(/[^0-9]/g, ''))}
            keyboardType="number-pad" maxLength={2} />
          <Field label={t('customSkills.description')} value={description} onChangeText={setDescription} multiline maxLength={1000} />
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <Btn title={t('common.cancel')} kind="ghost" style={{ flex: 1 }} onPress={() => { setOpen(false); setError(''); }} />
            <Btn title={t('customSkills.save')} style={{ flex: 1 }} busy={busy} onPress={add} />
          </View>
        </View>
      ) : (
        <Btn title={t('customSkills.add')} icon="add" kind="outline" style={{ marginTop: 6 }} onPress={() => setOpen(true)} />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginBottom: 12 },
  title: { fontSize: 18, fontFamily: 'Poppins_600SemiBold' },
  sub: { fontSize: 13, fontFamily: 'Poppins_400Regular' },
  item: { flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1, borderRadius: 10, padding: 10, marginBottom: 8 },
  name: { fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
});
