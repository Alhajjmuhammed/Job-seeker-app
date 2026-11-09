/**
 * The client's own job post: its review status, the applicants (shortlist,
 * not selected, hire), and the contracts that came out of it.
 */
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Modal, RefreshControl } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import {
  Badge, Btn, Card, Choice, DateField, Empty, ErrorBox, Field, Loading, Row, SectionTitle, Tag,
  apiError, formatDate, salaryText,
} from '../../../components/vacancies/ui';

interface Applicant {
  id: number;
  status: string;
  status_display: string;
  message: string;
  created_at: string;
  contract_id: number | null;
  worker: {
    id: number; user_id: number; name: string; worker_type: string; verified: boolean; city: string;
    experience_years: number; average_rating: string | null; completed_jobs: number; categories: string[];
    contracts_done: number;
  };
}

const BANNER: Record<string, { icon: any; key: string }> = {
  review: { icon: 'hourglass-outline', key: 'bannerReview' },
  changes: { icon: 'create-outline', key: 'bannerChanges' },
  rejected: { icon: 'close-circle-outline', key: 'bannerRejected' },
  published: { icon: 'megaphone-outline', key: 'bannerPublished' },
  filled: { icon: 'checkmark-done-outline', key: 'bannerFilled' },
  closed: { icon: 'lock-closed-outline', key: 'bannerClosed' },
};

export default function ClientVacancyScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { id } = useLocalSearchParams();
  const [v, setV] = useState<any>(null);
  const [apps, setApps] = useState<Applicant[]>([]);
  const [appsPage, setAppsPage] = useState(1);
  const [appsMore, setAppsMore] = useState(false);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<any>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [hiring, setHiring] = useState<Applicant | null>(null);
  const [hireStart, setHireStart] = useState('');
  const [hireTerms, setHireTerms] = useState('');

  const loadApps = useCallback(async (page = 1, status = filter) => {
    const data = await apiService.getVacancyApplicants(Number(id), status || undefined, page);
    const results: Applicant[] = data?.results || data || [];
    setApps(prev => (page === 1 ? results : [...prev, ...results]));
    setAppsPage(page);
    setAppsMore(!!data?.next);
  }, [id, filter]);

  const load = useCallback(async () => {
    try {
      const data = await apiService.getVacancy(Number(id));
      setV(data);
      if (data.can_manage) await loadApps(1);
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id, loadApps]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const changeFilter = async (f: string) => {
    setFilter(f);
    try { await loadApps(1, f); } catch (e: any) { Alert.alert(t('common.error'), apiError(e, t('vacancies.loadFailed'))); }
  };

  const decide = (a: Applicant, action: 'shortlist' | 'reject') => {
    const go = async () => {
      setBusyId(a.id);
      try {
        await apiService.applicationAction(a.id, action);
        await load();
      } catch (e: any) {
        Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed')));
      } finally {
        setBusyId(null);
      }
    };
    if (action === 'reject') {
      Alert.alert(t('vacancies.notSelect'), t('vacancies.notSelectConfirm', { name: a.worker.name }), [
        { text: t('common.cancel'), style: 'cancel' }, { text: t('vacancies.notSelect'), style: 'destructive', onPress: go },
      ]);
    } else go();
  };

  const hire = async () => {
    if (!hiring) return;
    setBusyId(hiring.id);
    try {
      const contract = await apiService.applicationAction(hiring.id, 'hire', {
        ...(hireStart ? { start_date: hireStart } : {}), terms: hireTerms.trim(),
      });
      setHiring(null);
      Alert.alert(t('vacancies.hiredTitle'), t('vacancies.hiredText'), [
        { text: t('common.ok'), onPress: () => router.push(`/(client)/contract/${contract.id}` as any) },
      ]);
      load();
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed')));
    } finally {
      setBusyId(null);
    }
  };

  const closeJob = () => Alert.alert(t('vacancies.closeJob'), t('vacancies.closeConfirm'), [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('vacancies.closeJob'), style: 'destructive', onPress: async () => {
      try { setV(await apiService.closeVacancy(Number(id))); load(); }
      catch (e: any) { Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed'))); }
    } },
  ]);

  const shell = (body: React.ReactNode) => (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <Header title={t('vacancies.jobPost')} showBack />
      {body}
    </View>
  );
  if (loading) return shell(<Loading />);
  if (error || !v) return shell(<ErrorBox message={apiError(error, t('vacancies.loadFailed'))} onRetry={() => { setLoading(true); load(); }} />);

  const banner = BANNER[v.status];
  const editable = ['review', 'changes', 'rejected'].includes(v.status);
  const closable = ['published', 'review', 'changes'].includes(v.status);
  const deciding = v.status === 'published';
  const filters = [
    { value: '', label: t('vacancies.all') },
    { value: 'applied', label: t('vacancies.appStatus.applied') },
    { value: 'shortlisted', label: t('vacancies.appStatus.shortlisted') },
    { value: 'hired', label: t('vacancies.appStatus.hired') },
    { value: 'not_selected', label: t('vacancies.appStatus.not_selected') },
  ];

  return shell(
    <>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} colors={[theme.primary]} />}>
        {banner && (
          <View style={[st.banner, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Ionicons name={banner.icon} size={22} color={theme.primary} />
            <View style={{ flex: 1 }}>
              <Text style={[st.bannerTitle, { color: theme.text }]}>{v.status_display}</Text>
              <Text style={[st.bannerText, { color: theme.textSecondary }]}>{t(`vacancies.${banner.key}`)}</Text>
              {!!v.review_note && ['changes', 'rejected'].includes(v.status) && (
                <Text style={[st.note, { color: theme.text }]}>{t('vacancies.adminNote')}: {v.review_note}</Text>
              )}
            </View>
          </View>
        )}

        <Card>
          <View style={st.top}>
            <Text style={[st.title, { color: theme.text }]}>{v.title}</Text>
            <Badge status={v.status} label={t(`status.${v.status}`, { defaultValue: v.status_display })} />
          </View>
          <Text style={[st.salary, { color: theme.primary }]}>{salaryText(v)}</Text>
          <Row label={t('vacancies.typeOfWork')} value={v.category_name} />
          <Row label={t('vacancies.howLong')} value={v.duration_display} />
          <Row label={t('vacancies.startDate')} value={formatDate(v.start_date)} />
          <Row label={t('vacancies.closingDate')} value={formatDate(v.closing_date)} />
          <Row label={t('vacancies.hired')} value={`${v.hired_count} / ${v.workers_needed}`} />
          <Row label={t('vacancies.where')} value={v.area ? `${v.area}, ${v.city}` : v.city} />
          <View style={st.actions}>
            {editable && <Btn title={t('vacancies.edit')} icon="create-outline" kind="outline" style={{ flex: 1 }}
              onPress={() => router.push(`/(client)/post-job?id=${v.id}` as any)} />}
            {closable && <Btn title={t('vacancies.closeJob')} icon="lock-closed-outline" kind="ghost" style={{ flex: 1 }} onPress={closeJob} />}
          </View>
        </Card>

        <SectionTitle>{t('vacancies.applicants')} ({v.applicant_count ?? apps.length})</SectionTitle>
        <Choice options={filters} value={filter} onChange={changeFilter} />
        {apps.length === 0 ? (
          <Empty icon="people-outline" title={t('vacancies.noApplicants')}
            text={v.status === 'published' ? t('vacancies.noApplicantsText') : t('vacancies.applicantsAfterPublish')} />
        ) : apps.map(a => (
          <Card key={a.id}>
            <View style={st.top}>
              <View style={{ flex: 1 }}>
                <Text style={[st.name, { color: theme.text }]}>{a.worker.name}</Text>
                <Text style={[st.sub, { color: theme.textSecondary }]}>
                  {a.worker.city}{a.worker.categories.length ? ` · ${a.worker.categories.slice(0, 3).join(', ')}` : ''}
                </Text>
              </View>
              <Badge status={a.status} label={t(`status.${a.status}`, { defaultValue: a.status_display })} />
            </View>
            <View style={st.tags}>
              {a.worker.verified && <Tag icon="shield-checkmark-outline" label={t('vacancies.verified')} />}
              <Tag icon="school-outline" label={t(`vacancies.workerTypes.${a.worker.worker_type}`)} />
              <Tag icon="briefcase-outline" label={t('vacancies.yearsExp', { count: a.worker.experience_years || 0 })} />
              {!!a.worker.average_rating && Number(a.worker.average_rating) > 0 && (
                <Tag icon="star-outline" label={Number(a.worker.average_rating).toFixed(1)} />
              )}
              <Tag icon="checkmark-done-outline" label={t('vacancies.jobsDone', { count: (a.worker.completed_jobs || 0) + (a.worker.contracts_done || 0) })} />
            </View>
            {!!a.message && <Text style={[st.message, { color: theme.text, borderColor: theme.border }]}>{a.message}</Text>}
            {deciding && ['applied', 'shortlisted'].includes(a.status) && (
              <View style={st.actions}>
                {a.status === 'applied' && (
                  <Btn title={t('vacancies.shortlist')} kind="outline" style={{ flex: 1 }} busy={busyId === a.id}
                    onPress={() => decide(a, 'shortlist')} />
                )}
                <Btn title={t('vacancies.hire')} style={{ flex: 1 }} disabled={busyId === a.id}
                  onPress={() => { setHireStart(''); setHireTerms(''); setHiring(a); }} />
                <Btn title={t('vacancies.notSelect')} kind="ghost" style={{ flex: 1 }} disabled={busyId === a.id}
                  onPress={() => decide(a, 'reject')} />
              </View>
            )}
            {a.status === 'hired' && !!a.contract_id && (
              <Btn title={t('vacancies.openContract')} kind="outline" icon="document-text-outline" style={{ marginTop: 10 }}
                onPress={() => router.push(`/(client)/contract/${a.contract_id}` as any)} />
            )}
          </Card>
        ))}
        {appsMore && <Btn title={t('vacancies.loadMore')} kind="ghost" onPress={() => loadApps(appsPage + 1).catch(() => {})} />}
      </ScrollView>

      <Modal visible={!!hiring} transparent animationType="slide" onRequestClose={() => setHiring(null)}>
        <View style={st.backdrop}>
          <View style={[st.sheet, { backgroundColor: theme.surface }]}>
            <Text style={[st.sheetTitle, { color: theme.text }]}>{t('vacancies.hireName', { name: hiring?.worker.name || '' })}</Text>
            <Text style={[st.sub, { color: theme.textSecondary, marginBottom: 12 }]}>{t('vacancies.hireExplain')}</Text>
            <DateField label={t('vacancies.startDateOptional')} value={hireStart} onChange={setHireStart} minimumDate={new Date()} />
            <Field label={t('vacancies.termsOptional')} value={hireTerms} onChangeText={setHireTerms} multiline maxLength={4000} />
            <View style={st.actions}>
              <Btn title={t('common.cancel')} kind="ghost" style={{ flex: 1 }} onPress={() => setHiring(null)} />
              <Btn title={t('vacancies.hire')} style={{ flex: 1 }} busy={!!hiring && busyId === hiring.id} onPress={hire} />
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

const st = StyleSheet.create({
  banner: { flexDirection: 'row', gap: 12, borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  bannerTitle: { fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  bannerText: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  note: { fontSize: 13, fontFamily: 'Poppins_500Medium', marginTop: 6 },
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' },
  title: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', flex: 1 },
  salary: { fontSize: 15, fontFamily: 'Poppins_700Bold', marginVertical: 6 },
  actions: { flexDirection: 'row', gap: 8, marginTop: 12 },
  name: { fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  sub: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  message: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 10, padding: 10, borderWidth: 1, borderRadius: 10 },
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20 },
  sheetTitle: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
});
