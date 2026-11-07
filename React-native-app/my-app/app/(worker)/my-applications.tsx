/** Jobs this worker applied for, with where each application stands. */
import React from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { usePaged } from '../../components/vacancies/usePaged';
import { Badge, Btn, Empty, ErrorBox, Loading, apiError, formatDate, salaryText } from '../../components/vacancies/ui';

interface MyApplication {
  id: number;
  status: string;
  status_display: string;
  created_at: string;
  contract_id: number | null;
  vacancy: { id: number; title: string; poster_name: string; city: string; area: string; duration_display: string;
    salary_amount: string; salary_max?: string | null; pay_period_display: string };
}

export default function MyApplicationsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const list = usePaged<MyApplication>((page) => apiService.getMyVacancyApplications(page));

  return (
    <View style={[st.c, { backgroundColor: theme.background }]}>
      <Header title={t('vacancies.myApplications')} showBack />
      <View style={st.actions}>
        <Btn title={t('vacancies.findJobs')} icon="search" onPress={() => router.push('/(worker)/find-jobs' as any)} style={{ flex: 1 }} />
        <Btn title={t('vacancies.myContracts')} icon="document-text-outline" kind="outline"
          onPress={() => router.push('/(worker)/contracts' as any)} style={{ flex: 1 }} />
      </View>
      {list.loading ? <Loading /> : list.error ? (
        <ErrorBox message={apiError(list.error, t('vacancies.loadFailed'))} onRetry={list.reload} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={a => String(a.id)}
          contentContainerStyle={{ padding: 16, paddingTop: 4 }}
          refreshControl={<RefreshControl refreshing={list.refreshing} onRefresh={list.refresh} colors={[theme.primary]} />}
          onEndReached={list.loadMore}
          onEndReachedThreshold={0.4}
          ListFooterComponent={list.loadingMore ? <ActivityIndicator color={theme.primary} style={{ margin: 16 }} /> : null}
          ListEmptyComponent={<Empty icon="paper-plane-outline" title={t('vacancies.noApplications')} text={t('vacancies.noApplicationsText')} />}
          renderItem={({ item: a }) => (
            <TouchableOpacity
              onPress={() => router.push((a.status === 'hired' && a.contract_id
                ? `/(worker)/contract/${a.contract_id}` : `/(worker)/vacancy/${a.vacancy.id}`) as any)}
              style={[st.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <View style={st.top}>
                <Text style={[st.title, { color: theme.text }]} numberOfLines={2}>{a.vacancy.title}</Text>
                <Badge status={a.status} label={a.status_display} />
              </View>
              <Text style={[st.sub, { color: theme.textSecondary }]}>
                {a.vacancy.poster_name} · {a.vacancy.area ? `${a.vacancy.area}, ${a.vacancy.city}` : a.vacancy.city}
              </Text>
              <Text style={[st.salary, { color: theme.primary }]}>{salaryText(a.vacancy)}</Text>
              <Text style={[st.sub, { color: theme.textSecondary }]}>{t('vacancies.appliedOn', { date: formatDate(a.created_at) })}</Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  c: { flex: 1 },
  actions: { flexDirection: 'row', gap: 10, padding: 16, paddingBottom: 8 },
  card: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 },
  title: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', flex: 1 },
  sub: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 3 },
  salary: { fontSize: 14, fontFamily: 'Poppins_700Bold', marginTop: 6 },
});
