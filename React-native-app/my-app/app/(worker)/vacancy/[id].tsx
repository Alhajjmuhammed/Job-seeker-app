/** One published job for a worker: details, Apply / Withdraw, Report. */
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, RefreshControl } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import ReportSheet from '../../../components/vacancies/ReportSheet';
import {
  Badge, Btn, Card, ErrorBox, Field, Loading, Row, SectionTitle, Tag, apiError, formatDate, salaryText,
} from '../../../components/vacancies/ui';

export default function WorkerVacancyScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { id } = useLocalSearchParams();
  const [v, setV] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [reporting, setReporting] = useState(false);

  const load = useCallback(async () => {
    try {
      setV(await apiService.getVacancy(Number(id)));
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useFocusEffect(useCallback(() => { setLoading(true); setMessage(''); load(); }, [load]));

  const apply = async () => {
    setBusy(true);
    try {
      await apiService.applyVacancy(Number(id), message.trim());
      setMessage('');
      Alert.alert(t('vacancies.appliedTitle'), t('vacancies.appliedText'));
      load();
    } catch (e: any) {
      Alert.alert(t('vacancies.cannotApply'), apiError(e, t('vacancies.actionFailed')));
      load();
    } finally {
      setBusy(false);
    }
  };

  const withdraw = () => Alert.alert(t('vacancies.withdraw'), t('vacancies.withdrawConfirm'), [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('vacancies.withdraw'), style: 'destructive', onPress: async () => {
      setBusy(true);
      try { await apiService.applicationAction(v.my_application.id, 'withdraw'); load(); }
      catch (e: any) { Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed'))); }
      finally { setBusy(false); }
    } },
  ]);

  const shell = (body: React.ReactNode) => (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <Header title={t('vacancies.job')} showBack />
      {body}
    </View>
  );
  if (loading) return shell(<Loading />);
  if (error || !v) return shell(<ErrorBox message={apiError(error, t('vacancies.jobNotFound'))} onRetry={() => { setLoading(true); load(); }} />);

  const mine = v.my_application;
  const activeApp = mine && ['applied', 'shortlisted'].includes(mine.status);
  const canApply = !v.apply_problem && (!mine || mine.status === 'withdrawn');

  return shell(
    <>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} colors={[theme.primary]} />}>
        <Card>
          <View style={st.top}>
            <Text style={[st.title, { color: theme.text }]}>{v.title}</Text>
            {v.status !== 'published' && <Badge status={v.status} label={t(`status.${v.status}`, { defaultValue: v.status_display })} />}
          </View>
          <Text style={[st.poster, { color: theme.textSecondary }]}>{v.poster_name} · {v.kind_display}</Text>
          <Text style={[st.salary, { color: theme.primary }]}>{salaryText(v)}</Text>
          <View style={st.tags}>
            <Tag icon="location-outline" label={v.area ? `${v.area}, ${v.city}` : v.city} />
            <Tag icon="time-outline" label={v.duration_display} />
            <Tag icon="people-outline" label={t('vacancies.placesLeft', { count: v.places_left, total: v.workers_needed })} />
            {v.worker_type_needed !== 'any' && <Tag icon="school-outline" label={v.worker_type_display} />}
            {v.live_in && <Tag icon="home-outline" label={t('vacancies.liveIn')} />}
            {v.food_provided && <Tag icon="restaurant-outline" label={t('vacancies.food')} />}
            {v.room_provided && <Tag icon="bed-outline" label={t('vacancies.room')} />}
          </View>
        </Card>

        <Card>
          <SectionTitle>{t('vacancies.aboutJob')}</SectionTitle>
          <Text style={[st.body, { color: theme.text }]}>{v.description}</Text>
          {!!v.duties && <><Text style={[st.label, { color: theme.textSecondary }]}>{t('vacancies.duties')}</Text>
            <Text style={[st.body, { color: theme.text }]}>{v.duties}</Text></>}
          {!!v.requirements && <><Text style={[st.label, { color: theme.textSecondary }]}>{t('vacancies.requirements')}</Text>
            <Text style={[st.body, { color: theme.text }]}>{v.requirements}</Text></>}
        </Card>

        <Card>
          <Row label={t('vacancies.typeOfWork')} value={v.category_name} />
          <Row label={t('vacancies.startDate')} value={formatDate(v.start_date)} />
          <Row label={t('vacancies.closingDate')} value={formatDate(v.closing_date)} />
          <Row label={t('vacancies.payDay')} value={v.pay_day} />
          <Row label={t('vacancies.workingDays')} value={v.working_days} />
          <Row label={t('vacancies.workingHours')} value={v.working_hours} />
          <Row label={t('vacancies.trialPeriod')} value={v.trial_period} />
          <Row label={t('vacancies.address')} value={v.address} />
          {!v.address && <Text style={[st.hint, { color: theme.textSecondary }]}>{t('vacancies.addressAfterHire')}</Text>}
        </Card>

        {mine && mine.status !== 'withdrawn' ? (
          <Card>
            <View style={st.top}>
              <Text style={[st.label, { color: theme.text, marginTop: 0 }]}>{t('vacancies.yourApplication')}</Text>
              <Badge status={mine.status} label={t(`status.${mine.status}`, { defaultValue: mine.status_display })} />
            </View>
            <Text style={[st.hint, { color: theme.textSecondary }]}>{t(`vacancies.appExplain.${mine.status}`)}</Text>
            {activeApp && <Btn title={t('vacancies.withdraw')} kind="ghost" onPress={withdraw} busy={busy} style={{ marginTop: 10 }} />}
            {mine.status === 'hired' && !!mine.contract_id && (
              <Btn title={t('vacancies.openContract')} icon="document-text-outline" style={{ marginTop: 10 }}
                onPress={() => router.push(`/(worker)/contract/${mine.contract_id}` as any)} />
            )}
          </Card>
        ) : canApply ? (
          <Card>
            <SectionTitle>{t('vacancies.applyNow')}</SectionTitle>
            <Field label={t('vacancies.messageOptional')} value={message} onChangeText={setMessage} multiline maxLength={2000}
              placeholder={t('vacancies.messagePlaceholder')} />
            <Btn title={t('vacancies.apply')} icon="paper-plane-outline" onPress={apply} busy={busy} />
          </Card>
        ) : (
          <View style={[st.problem, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Ionicons name="information-circle-outline" size={20} color={theme.textSecondary} />
            <Text style={[st.hint, { color: theme.text, flex: 1, marginTop: 0 }]}>{v.apply_problem}</Text>
          </View>
        )}

        <Btn title={t('vacancies.reportJob')} icon="flag-outline" kind="ghost" onPress={() => setReporting(true)} style={{ marginTop: 6 }} />
      </ScrollView>
      <ReportSheet visible={reporting} onClose={() => setReporting(false)}
        send={(type, text) => apiService.reportVacancy(Number(id), type, text)} />
    </>
  );
}

const st = StyleSheet.create({
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' },
  title: { fontSize: 19, fontFamily: 'Poppins_600SemiBold', flex: 1 },
  poster: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  salary: { fontSize: 16, fontFamily: 'Poppins_700Bold', marginTop: 8 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  body: { fontSize: 14, fontFamily: 'Poppins_400Regular', lineHeight: 21 },
  label: { fontSize: 13, fontFamily: 'Poppins_600SemiBold', marginTop: 12, marginBottom: 4 },
  hint: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 6 },
  problem: { flexDirection: 'row', gap: 10, alignItems: 'center', borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 12 },
});
