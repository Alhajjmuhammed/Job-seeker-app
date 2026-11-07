/**
 * Job board: jobs the admin team has published. Every worker can look; the
 * server decides who can apply (verified, and the worker type the job asks for).
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, ActivityIndicator, TextInput, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import VacancyCard, { VacancySummary } from '../../components/vacancies/VacancyCard';
import { usePaged } from '../../components/vacancies/usePaged';
import { Btn, Choice, Empty, ErrorBox, Loading, Toggle, apiError } from '../../components/vacancies/ui';

export default function FindJobsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [q, setQ] = useState('');
  const [city, setCity] = useState('');
  const [duration, setDuration] = useState('');
  const [kind, setKind] = useState('');
  const [onlyMine, setOnlyMine] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  // what the list was last loaded with (typing does not reload on every key)
  const [applied, setApplied] = useState({ q: '', city: '' });

  const list = usePaged<VacancySummary>((page) => apiService.getVacancies({
    page, q: applied.q || undefined, city: applied.city || undefined,
    duration: duration || undefined, kind: kind || undefined, only_mine: onlyMine ? 1 : undefined,
  }), [applied.q, applied.city, duration, kind, onlyMine]);

  const search = () => setApplied({ q: q.trim(), city: city.trim() });

  const durations = [
    { value: '', label: t('vacancies.anyLength') },
    ...['one_off', '1_month', '3_months', '6_months', '12_months', 'permanent'].map(v => ({ value: v, label: t(`vacancies.durations.${v}`) })),
  ];
  const kinds = [
    { value: '', label: t('vacancies.all') },
    { value: 'home', label: t('vacancies.kindHomeShort') },
    { value: 'business', label: t('vacancies.kindBusinessShort') },
  ];

  return (
    <View style={[st.c, { backgroundColor: theme.background }]}>
      <Header title={t('vacancies.findJobs')} showBack />
      <View style={[st.searchBar, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        <View style={st.searchRow}>
          <TextInput value={q} onChangeText={setQ} onSubmitEditing={search} returnKeyType="search"
            placeholder={t('vacancies.searchJobs')} placeholderTextColor={theme.textSecondary}
            style={[st.input, { flex: 2, color: theme.text, backgroundColor: theme.background, borderColor: theme.border }]} />
          <TextInput value={city} onChangeText={setCity} onSubmitEditing={search} returnKeyType="search"
            placeholder={t('vacancies.city')} placeholderTextColor={theme.textSecondary}
            style={[st.input, { flex: 1, color: theme.text, backgroundColor: theme.background, borderColor: theme.border }]} />
          <TouchableOpacity onPress={search} style={[st.iconBtn, { backgroundColor: theme.primary }]} accessibilityLabel={t('vacancies.search')}>
            <Ionicons name="search" size={18} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
        <TouchableOpacity onPress={() => setShowFilters(x => !x)} style={st.filterToggle}>
          <Ionicons name="options-outline" size={16} color={theme.primary} />
          <Text style={[st.filterText, { color: theme.primary }]}>{showFilters ? t('vacancies.hideFilters') : t('vacancies.filters')}</Text>
        </TouchableOpacity>
        {showFilters && (
          <View>
            <Choice label={t('vacancies.howLong')} options={durations} value={duration} onChange={setDuration} />
            <Choice label={t('vacancies.whoHiring')} options={kinds} value={kind} onChange={setKind} />
            <Toggle label={t('vacancies.onlyMyType')} value={onlyMine} onChange={setOnlyMine} />
          </View>
        )}
      </View>

      {list.loading ? <Loading /> : list.error ? (
        <ErrorBox message={apiError(list.error, t('vacancies.loadFailed'))} onRetry={list.reload} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={v => String(v.id)}
          contentContainerStyle={{ padding: 16 }}
          refreshControl={<RefreshControl refreshing={list.refreshing} onRefresh={list.refresh} colors={[theme.primary]} />}
          onEndReached={list.loadMore}
          onEndReachedThreshold={0.4}
          ListHeaderComponent={list.count ? (
            <Text style={[st.count, { color: theme.textSecondary }]}>{t('vacancies.jobsFound', { count: list.count })}</Text>
          ) : null}
          ListFooterComponent={list.loadingMore ? <ActivityIndicator color={theme.primary} style={{ margin: 16 }} /> : null}
          ListEmptyComponent={<Empty title={t('vacancies.noJobs')} text={t('vacancies.noJobsText')}
            action={<Btn title={t('vacancies.myApplications')} kind="outline" style={{ marginTop: 14 }}
              onPress={() => router.push('/(worker)/my-applications' as any)} />} />}
          renderItem={({ item }) => <VacancyCard v={item} onPress={() => router.push(`/(worker)/vacancy/${item.id}` as any)} />}
        />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  c: { flex: 1 },
  searchBar: { padding: 12, borderBottomWidth: 1 },
  searchRow: { flexDirection: 'row', gap: 8 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9, fontSize: 14, fontFamily: 'Poppins_400Regular' },
  iconBtn: { width: 42, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  filterToggle: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 10, marginBottom: 4 },
  filterText: { fontSize: 13, fontFamily: 'Poppins_600SemiBold' },
  count: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginBottom: 8 },
});
