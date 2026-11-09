/**
 * One contract - shared by the employer (client app) and the worker.
 * The server decides what each side may do; this screen only offers the
 * buttons that make sense for the contract's state and the viewer's role.
 */
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Linking, Modal, TouchableOpacity, RefreshControl } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../Header';
import apiService from '../../services/api';
import ReportSheet from './ReportSheet';
import { Badge, Btn, Card, Choice, ErrorBox, Field, Loading, Row, SectionTitle, apiError, formatDate, salaryText } from './ui';

interface Contract {
  id: number;
  my_role: 'employer' | 'worker' | 'admin' | null;
  vacancy: { id: number; title: string; city: string; area: string; duration_display: string; poster_name: string };
  worker_name: string;
  worker_user_id: number;
  employer_name: string;
  employer_user_id: number;
  start_date: string;
  end_date: string | null;
  salary_amount: string;
  pay_period_display: string;
  terms: string;
  status: string;
  status_display: string;
  end_reason: string;
  employer_rating: number | null;
  employer_feedback: string;
  worker_rating: number | null;
  worker_feedback: string;
  renewed_to: number | null;
  renewed_from: number | null;
  address: string;
  other_phone?: string;
  relationship_open?: boolean;
}

type Mode = 'end' | 'renew' | 'rate' | null;

export default function ContractView({ group }: { group: '(client)' | '(worker)' }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { id } = useLocalSearchParams();
  const [c, setC] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<any>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [reporting, setReporting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState('3_months');
  const [stars, setStars] = useState(0);
  const [feedback, setFeedback] = useState('');

  const load = useCallback(async () => {
    try {
      setC(await apiService.getContract(Number(id)));
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  const act = async (action: string, data: Record<string, any>) => {
    setBusy(true);
    try {
      const updated = await apiService.contractAction(Number(id), action, data);
      setMode(null);
      if (action === 'renew' && updated?.id && updated.id !== Number(id)) {
        Alert.alert(t('vacancies.renewed'), t('vacancies.renewedText'));
        router.replace(`/${group}/contract/${updated.id}` as any);
        return;
      }
      setC(updated);
      Alert.alert(t('common.success'), t(`vacancies.done.${action}`));
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed')));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Shell title={t('vacancies.contract')}><Loading /></Shell>;
  if (error || !c) {
    return <Shell title={t('vacancies.contract')}>
      <ErrorBox message={apiError(error, t('vacancies.loadFailed'))} onRetry={() => { setLoading(true); load(); }} />
    </Shell>;
  }

  const isEmployer = c.my_role === 'employer';
  const isWorker = c.my_role === 'worker';
  const otherId = isEmployer ? c.worker_user_id : c.employer_user_id;
  // the server closes chat/contact for the whole hire once a contract is ended early (renewals too)
  const canTalk = (isEmployer || isWorker) && c.status !== 'ended_early' && c.relationship_open !== false;
  const myRating = isEmployer ? c.employer_rating : isWorker ? c.worker_rating : null;
  const canRate = (isEmployer || isWorker) && c.status !== 'active' && !myRating;
  const canRenew = isEmployer && ['active', 'finished'].includes(c.status) && !c.renewed_to;

  const call = () => c.other_phone && Linking.openURL(`tel:${c.other_phone}`).catch(() =>
    Alert.alert(t('common.error'), t('messages.cannotCall')));

  const renewOptions = ['1_month', '3_months', '6_months', '12_months', 'permanent']
    .map(v => ({ value: v, label: t(`vacancies.durations.${v}`) }));

  return (
    <Shell title={t('vacancies.contract')}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} colors={[theme.primary]} />}>
        <Card>
          <View style={st.top}>
            <Text style={[st.title, { color: theme.text }]}>{c.vacancy.title}</Text>
            <Badge status={c.status} label={t(`status.${c.status}`, { defaultValue: c.status_display })} />
          </View>
          <Text style={[st.salary, { color: theme.primary }]}>{salaryText(c)}</Text>
          <Row label={t('vacancies.employer')} value={c.employer_name} />
          <Row label={t('vacancies.worker')} value={c.worker_name} />
          <Row label={t('vacancies.startDate')} value={formatDate(c.start_date)} />
          <Row label={t('vacancies.endDate')} value={c.end_date ? formatDate(c.end_date) : t('vacancies.noEndDate')} />
          <Row label={t('vacancies.address')} value={c.address} />
          {!!c.end_reason && <Row label={t('vacancies.endReason')} value={c.end_reason} />}
        </Card>

        {!!c.terms && (
          <Card>
            <SectionTitle>{t('vacancies.terms')}</SectionTitle>
            <Text style={{ color: theme.text, fontFamily: 'Poppins_400Regular', lineHeight: 20 }}>{c.terms}</Text>
          </Card>
        )}

        {canTalk && (
          <View style={st.actionsRow}>
            <Btn title={t('vacancies.chat')} icon="chatbubbles-outline" kind="outline" style={{ flex: 1 }}
              onPress={() => router.push(`/${group}/conversation/${otherId}` as any)} />
            {!!c.other_phone && (
              <Btn title={t('messages.call')} icon="call" style={{ flex: 1 }} onPress={call} />
            )}
          </View>
        )}

        {(c.employer_rating || c.worker_rating) ? (
          <Card>
            <SectionTitle>{t('vacancies.ratings')}</SectionTitle>
            {!!c.employer_rating && <Row label={t('vacancies.employerRated')} value={'★'.repeat(c.employer_rating)} />}
            {!!c.employer_feedback && <Text style={[st.feedback, { color: theme.textSecondary }]}>“{c.employer_feedback}”</Text>}
            {!!c.worker_rating && <Row label={t('vacancies.workerRated')} value={'★'.repeat(c.worker_rating)} />}
            {!!c.worker_feedback && <Text style={[st.feedback, { color: theme.textSecondary }]}>“{c.worker_feedback}”</Text>}
          </Card>
        ) : null}

        <View style={{ gap: 10 }}>
          {canRate && <Btn title={t('vacancies.rate')} icon="star-outline" onPress={() => { setStars(0); setFeedback(''); setMode('rate'); }} />}
          {canRenew && <Btn title={t('vacancies.renew')} icon="refresh" kind="outline" onPress={() => setMode('renew')} />}
          {c.status === 'active' && (isEmployer || isWorker) && (
            <Btn title={t('vacancies.endContract')} icon="stop-circle-outline" kind="outline" onPress={() => { setReason(''); setMode('end'); }} />
          )}
          {!!c.renewed_to && <Btn title={t('vacancies.openRenewal')} kind="ghost" onPress={() => router.push(`/${group}/contract/${c.renewed_to}` as any)} />}
          {!!c.renewed_from && <Btn title={t('vacancies.openPrevious')} kind="ghost" onPress={() => router.push(`/${group}/contract/${c.renewed_from}` as any)} />}
          <Btn title={t('vacancies.report')} icon="flag-outline" kind="ghost" onPress={() => setReporting(true)} />
        </View>
      </ScrollView>

      <Modal visible={mode !== null} transparent animationType="slide" onRequestClose={() => setMode(null)}>
        <View style={st.backdrop}>
          <View style={[st.sheet, { backgroundColor: theme.surface }]}>
            {mode === 'end' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>{t('vacancies.endContract')}</Text>
                <Text style={[st.note, { color: theme.textSecondary }]}>{t('vacancies.endExplain')}</Text>
                <Field label={t('vacancies.endReason')} value={reason} onChangeText={setReason} multiline maxLength={2000} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('vacancies.endContract')} danger
                  onOk={() => reason.trim() ? act('end', { reason: reason.trim() }) : Alert.alert(t('vacancies.endContract'), t('vacancies.needReason'))} />
              </>
            )}
            {mode === 'renew' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>{t('vacancies.renew')}</Text>
                <Choice label={t('vacancies.renewFor')} options={renewOptions} value={duration} onChange={setDuration} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('vacancies.renew')}
                  onOk={() => act('renew', { duration })} />
              </>
            )}
            {mode === 'rate' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>
                  {isEmployer ? t('vacancies.rateWorker') : t('vacancies.rateEmployer')}
                </Text>
                <View style={st.stars}>
                  {[1, 2, 3, 4, 5].map(n => (
                    <TouchableOpacity key={n} onPress={() => setStars(n)} accessibilityLabel={`${n}`}>
                      <Ionicons name={n <= stars ? 'star' : 'star-outline'} size={36} color="#F59E0B" />
                    </TouchableOpacity>
                  ))}
                </View>
                <Field label={t('vacancies.feedback')} value={feedback} onChangeText={setFeedback} multiline maxLength={2000} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('vacancies.sendRating')}
                  onOk={() => stars ? act('rate', { rating: stars, feedback: feedback.trim() }) : Alert.alert(t('vacancies.rate'), t('vacancies.chooseStars'))} />
              </>
            )}
          </View>
        </View>
      </Modal>

      <ReportSheet visible={reporting} onClose={() => setReporting(false)}
        send={(type, text) => apiService.contractAction(Number(id), 'report', { report_type: type, description: text })} />
    </Shell>
  );
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  const { theme } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <Header title={title} showBack />
      {children}
    </View>
  );
}

function SheetButtons({ onCancel, onOk, okTitle, busy, danger }: {
  onCancel: () => void; onOk: () => void; okTitle: string; busy: boolean; danger?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <View style={st.actionsRow}>
      <Btn title={t('common.cancel')} kind="ghost" onPress={onCancel} style={{ flex: 1 }} />
      <Btn title={okTitle} kind={danger ? 'danger' : 'primary'} onPress={onOk} busy={busy} style={{ flex: 1 }} />
    </View>
  );
}

const st = StyleSheet.create({
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: 10, marginBottom: 4 },
  title: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', flex: 1 },
  salary: { fontSize: 15, fontFamily: 'Poppins_700Bold', marginBottom: 8 },
  actionsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  feedback: { fontSize: 13, fontStyle: 'italic', marginBottom: 6 },
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20 },
  sheetTitle: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', marginBottom: 10 },
  note: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginBottom: 12 },
  stars: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginVertical: 12 },
});
