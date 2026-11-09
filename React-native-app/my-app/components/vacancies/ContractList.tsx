/** "My contracts" - the same screen for the employer (client) and the worker. */
import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../Header';
import apiService from '../../services/api';
import { usePaged } from './usePaged';
import { Badge, Choice, Empty, ErrorBox, Loading, formatDate, salaryText, apiError } from './ui';

export interface ContractSummary {
  id: number;
  my_role: 'employer' | 'worker' | 'admin' | null;
  vacancy: { id: number; title: string; city: string; area: string; duration_display: string };
  worker_name: string;
  employer_name: string;
  start_date: string;
  end_date: string | null;
  salary_amount: string;
  pay_period_display: string;
  status: string;
  status_display: string;
}

export default function ContractList({ group }: { group: '(client)' | '(worker)' }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [status, setStatus] = useState('');
  const list = usePaged<ContractSummary>((page) => apiService.getContracts(status || undefined, page), [status]);

  const filters = [
    { value: '', label: t('vacancies.all') },
    { value: 'active', label: t('vacancies.contractStatus.active') },
    { value: 'finished', label: t('vacancies.contractStatus.finished') },
    { value: 'ended_early', label: t('vacancies.contractStatus.ended_early') },
  ];

  return (
    <View style={[st.container, { backgroundColor: theme.background }]}>
      <Header title={t('vacancies.myContracts')} showBack />
      <View style={st.filters}><Choice options={filters} value={status} onChange={setStatus} /></View>
      {list.loading ? <Loading /> : list.error ? (
        <ErrorBox message={apiError(list.error, t('vacancies.loadFailed'))} onRetry={list.reload} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={c => String(c.id)}
          contentContainerStyle={{ padding: 16, paddingTop: 4 }}
          refreshControl={<RefreshControl refreshing={list.refreshing} onRefresh={list.refresh} colors={[theme.primary]} />}
          onEndReached={list.loadMore}
          onEndReachedThreshold={0.4}
          ListFooterComponent={list.loadingMore ? <ActivityIndicator color={theme.primary} style={{ margin: 16 }} /> : null}
          ListEmptyComponent={<Empty icon="document-text-outline" title={t('vacancies.noContracts')}
            text={group === '(client)' ? t('vacancies.noContractsClient') : t('vacancies.noContractsWorker')} />}
          renderItem={({ item: c }) => (
            <TouchableOpacity onPress={() => router.push(`/${group}/contract/${c.id}` as any)}
              style={[st.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <View style={st.top}>
                <Text style={[st.title, { color: theme.text }]} numberOfLines={2}>{c.vacancy.title}</Text>
                <Badge status={c.status} label={t(`status.${c.status}`, { defaultValue: c.status_display })} />
              </View>
              <Text style={[st.sub, { color: theme.textSecondary }]}>
                {c.my_role === 'worker' ? c.employer_name : c.worker_name}
              </Text>
              <Text style={[st.salary, { color: theme.primary }]}>{salaryText(c)}</Text>
              <Text style={[st.sub, { color: theme.textSecondary }]}>
                {formatDate(c.start_date)} → {c.end_date ? formatDate(c.end_date) : t('vacancies.noEndDate')}
              </Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  container: { flex: 1 },
  filters: { paddingHorizontal: 16, paddingTop: 12 },
  card: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 },
  title: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', flex: 1 },
  sub: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 3 },
  salary: { fontSize: 14, fontFamily: 'Poppins_700Bold', marginTop: 6 },
});
