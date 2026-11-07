/** The client's job posts: under review, published, filled, closed. */
import React from 'react';
import { View, FlatList, RefreshControl, ActivityIndicator, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import VacancyCard, { VacancySummary } from '../../components/vacancies/VacancyCard';
import { usePaged } from '../../components/vacancies/usePaged';
import { Btn, Empty, ErrorBox, Loading, apiError } from '../../components/vacancies/ui';

export default function MyJobsScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const list = usePaged<VacancySummary>((page) => apiService.getMyVacancies(page));

  return (
    <View style={[st.c, { backgroundColor: theme.background }]}>
      <Header title={t('vacancies.myJobs')} showBack />
      <View style={st.actions}>
        <Btn title={t('vacancies.postJob')} icon="add" onPress={() => router.push('/(client)/post-job' as any)} style={{ flex: 1 }} />
        <Btn title={t('vacancies.myContracts')} icon="document-text-outline" kind="outline"
          onPress={() => router.push('/(client)/contracts' as any)} style={{ flex: 1 }} />
      </View>
      {list.loading ? <Loading /> : list.error ? (
        <ErrorBox message={apiError(list.error, t('vacancies.loadFailed'))} onRetry={list.reload} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={v => String(v.id)}
          contentContainerStyle={{ padding: 16, paddingTop: 4 }}
          refreshControl={<RefreshControl refreshing={list.refreshing} onRefresh={list.refresh} colors={[theme.primary]} />}
          onEndReached={list.loadMore}
          onEndReachedThreshold={0.4}
          ListFooterComponent={list.loadingMore ? <ActivityIndicator color={theme.primary} style={{ margin: 16 }} /> : null}
          ListEmptyComponent={<Empty title={t('vacancies.noPosts')} text={t('vacancies.noPostsText')} />}
          renderItem={({ item }) => (
            <VacancyCard v={item} showStatus onPress={() => router.push(`/(client)/vacancy/${item.id}` as any)} />
          )}
        />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  c: { flex: 1 },
  actions: { flexDirection: 'row', gap: 10, padding: 16, paddingBottom: 8 },
});
