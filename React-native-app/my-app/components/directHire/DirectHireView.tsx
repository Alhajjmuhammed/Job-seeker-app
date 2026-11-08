/**
 * One direct booking - shared by the client (who booked) and the worker.
 * The server says what this viewer may do (can_accept, can_complete, ...);
 * this screen only shows those buttons. Address and phones arrive only once
 * the worker has accepted.
 */
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, Linking, Modal, TouchableOpacity, RefreshControl, Image } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../Header';
import apiService from '../../services/api';
import { Badge, Btn, Card, ErrorBox, Field, Loading, Row, SectionTitle, apiError, formatMoney } from '../vacancies/ui';
import { DirectHire, durationText, hireTone, rateText, startText } from './common';

type Mode = 'complete' | 'cancel' | 'decline' | null;

export default function DirectHireView({ group }: { group: '(client)' | '(worker)' }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { id } = useLocalSearchParams();
  const [h, setH] = useState<DirectHire | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<any>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState('');
  const [stars, setStars] = useState(0);
  const [feedback, setFeedback] = useState('');

  const load = useCallback(async () => {
    try {
      setH(await apiService.getDirectHire(Number(id)));
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useFocusEffect(useCallback(() => { setLoading(true); load(); }, [load]));

  /** Run an action, show its message, reload the booking. */
  const run = async (fn: () => Promise<any>, doneKey: string) => {
    setBusy(true);
    try {
      await fn();
      setMode(null);
      Alert.alert(t('common.success'), t(doneKey));
      await load();
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('directHire.actionFailed')));
      load(); // the state may have changed under us (e.g. the other side cancelled)
    } finally {
      setBusy(false);
    }
  };

  const title = t('directHire.booking');
  if (loading) return <Shell title={title}><Loading /></Shell>;
  if (error || !h) {
    return <Shell title={title}>
      <ErrorBox message={apiError(error, t('directHire.loadFailed'))} onRetry={() => { setLoading(true); load(); }} />
    </Shell>;
  }

  const isClient = h.my_role === 'client';
  const other = isClient
    ? { userId: h.worker.user_id, name: h.worker.full_name, phone: h.worker.phone }
    : { userId: h.client.id, name: h.client.full_name, phone: h.client.phone };

  const call = () => other.phone && Linking.openURL(`tel:${other.phone}`).catch(() =>
    Alert.alert(t('common.error'), t('messages.cannotCall')));
  const chat = () => router.push(`/${group}/conversation/${other.userId}?name=${encodeURIComponent(other.name)}` as any);

  const accept = () => Alert.alert(t('directHire.acceptTitle'), t('directHire.acceptConfirm'), [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('directHire.accept'), onPress: () => run(() => apiService.acceptDirectHireRequest(h.id), 'directHire.acceptedMsg') },
  ]);

  return (
    <Shell title={title}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} colors={[theme.primary]} />}>
        <Card>
          <View style={st.top}>
            <Text style={[st.title, { color: theme.text }]}>{h.title}</Text>
            <Badge status={hireTone(h.status)} label={h.status_display} />
          </View>
          <Text style={[st.money, { color: theme.primary }]}>TSh {formatMoney(h.total_amount)}</Text>
          <Row label={t('directHire.rate')} value={rateText(t, h)} />
          <Row label={t('directHire.duration')} value={durationText(t, h)} />
          <Row label={t('directHire.starts')} value={startText(h.start_datetime)} />
          <Row label={t('directHire.requested')} value={startText(h.created_at)} />
          {h.location_hidden ? (
            <View style={st.hidden}>
              <Ionicons name="lock-closed-outline" size={14} color={theme.textSecondary} />
              <Text style={[st.hiddenText, { color: theme.textSecondary }]}>{t('directHire.locationHidden')}</Text>
            </View>
          ) : (
            <Row label={t('directHire.location')} value={h.location} />
          )}
        </Card>

        {!!h.description && (
          <Card>
            <SectionTitle>{t('directHire.description')}</SectionTitle>
            <Text style={[st.body, { color: theme.text }]}>{h.description}</Text>
          </Card>
        )}

        {/* the other side */}
        <Card>
          <SectionTitle>{isClient ? t('directHire.worker') : t('directHire.client')}</SectionTitle>
          <View style={st.person}>
            {isClient && h.worker.profile_picture ? (
              <Image source={{ uri: h.worker.profile_picture }} style={st.avatar} />
            ) : (
              <View style={[st.avatar, st.avatarEmpty, { backgroundColor: theme.primary }]}>
                <Text style={st.initial}>{(other.name || '?').charAt(0).toUpperCase()}</Text>
              </View>
            )}
            <View style={{ flex: 1 }}>
              <Text style={[st.name, { color: theme.text }]}>{other.name}</Text>
              {isClient && (
                <View style={st.meta}>
                  <Ionicons name="star" size={13} color="#F59E0B" />
                  <Text style={[st.metaText, { color: theme.textSecondary }]}>{Number(h.worker.rating || 0).toFixed(1)}</Text>
                </View>
              )}
              {!!other.phone && <Text style={[st.metaText, { color: theme.textSecondary }]}>{other.phone}</Text>}
            </View>
          </View>
          {h.can_chat && (
            <View style={[st.actionsRow, { marginTop: 12, marginBottom: 0 }]}>
              <Btn title={t('vacancies.chat')} icon="chatbubbles-outline" kind="outline" style={{ flex: 1 }} onPress={chat} />
              {!!other.phone && <Btn title={t('messages.call')} icon="call" style={{ flex: 1 }} onPress={call} />}
            </View>
          )}
        </Card>

        {(!!h.worker_response_message || !!h.client_rating) && (
          <Card>
            {!!h.worker_response_message && <Row label={t('directHire.workerNote')} value={h.worker_response_message} />}
            {!!h.client_rating && (
              <Row label={isClient ? t('directHire.yourRating') : t('directHire.clientRating')} value={'★'.repeat(h.client_rating)} />
            )}
            {!!h.client_feedback && <Text style={[st.feedback, { color: theme.textSecondary }]}>“{h.client_feedback}”</Text>}
          </Card>
        )}

        {h.worker_busy && (
          <View style={[st.notice, { backgroundColor: '#FEF3C7' }]}>
            <Ionicons name="alert-circle-outline" size={18} color="#92400E" />
            <Text style={st.noticeText}>{t('directHire.busy')}</Text>
          </View>
        )}

        <View style={{ gap: 10 }}>
          {h.can_accept && <Btn title={t('directHire.accept')} icon="checkmark-circle-outline" busy={busy} onPress={accept} />}
          {h.can_decline && (
            <Btn title={t('directHire.decline')} icon="close-circle-outline" kind="outline"
              onPress={() => { setReason(''); setMode('decline'); }} />
          )}
          {h.can_complete && (
            <Btn title={t('directHire.complete')} icon="checkmark-done-outline"
              onPress={() => { setStars(0); setFeedback(''); setMode('complete'); }} />
          )}
          {h.can_cancel && (
            <Btn title={t('directHire.cancelBooking')} icon="stop-circle-outline" kind="ghost"
              onPress={() => { setReason(''); setMode('cancel'); }} />
          )}
        </View>
      </ScrollView>

      <Modal visible={mode !== null} transparent animationType="slide" onRequestClose={() => setMode(null)}>
        <View style={st.backdrop}>
          <View style={[st.sheet, { backgroundColor: theme.surface }]}>
            {mode === 'decline' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>{t('directHire.declineTitle')}</Text>
                <Field label={t('directHire.declineReason')} value={reason} onChangeText={setReason} multiline maxLength={500} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('directHire.decline')} danger
                  onOk={() => run(() => apiService.rejectDirectHireRequest(h.id, reason.trim()), 'directHire.declinedMsg')} />
              </>
            )}
            {mode === 'cancel' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>{t('directHire.cancelBooking')}</Text>
                <Text style={[st.note, { color: theme.textSecondary }]}>{t('directHire.cancelExplain')}</Text>
                <Field label={t('directHire.cancelReason')} value={reason} onChangeText={setReason} multiline maxLength={500} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('directHire.cancelBooking')} danger
                  onOk={() => run(() => apiService.cancelDirectHire(h.id, reason.trim()), 'directHire.cancelledMsg')} />
              </>
            )}
            {mode === 'complete' && (
              <>
                <Text style={[st.sheetTitle, { color: theme.text }]}>{t('directHire.completeTitle')}</Text>
                <View style={st.stars}>
                  {[1, 2, 3, 4, 5].map(n => (
                    <TouchableOpacity key={n} onPress={() => setStars(n)} accessibilityLabel={`${n}`}>
                      <Ionicons name={n <= stars ? 'star' : 'star-outline'} size={36} color="#F59E0B" />
                    </TouchableOpacity>
                  ))}
                </View>
                <Field label={t('directHire.feedback')} value={feedback} onChangeText={setFeedback} multiline maxLength={2000} />
                <SheetButtons busy={busy} onCancel={() => setMode(null)} okTitle={t('directHire.completeOk')}
                  onOk={() => run(() => apiService.completeDirectHire(h.id, { rating: stars || null, feedback: feedback.trim() }),
                    'directHire.completedMsg')} />
              </>
            )}
          </View>
        </View>
      </Modal>
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
  money: { fontSize: 16, fontFamily: 'Poppins_700Bold', marginBottom: 8 },
  body: { fontFamily: 'Poppins_400Regular', lineHeight: 20 },
  hidden: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6 },
  hiddenText: { fontSize: 13, fontFamily: 'Poppins_400Regular', flex: 1 },
  person: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatar: { width: 48, height: 48, borderRadius: 24 },
  avatarEmpty: { alignItems: 'center', justifyContent: 'center' },
  initial: { color: '#FFFFFF', fontSize: 18, fontFamily: 'Poppins_700Bold' },
  name: { fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  metaText: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  actionsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  feedback: { fontSize: 13, fontStyle: 'italic', marginBottom: 6 },
  notice: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', padding: 12, borderRadius: 12, marginBottom: 12 },
  noticeText: { flex: 1, color: '#92400E', fontSize: 13, fontFamily: 'Poppins_500Medium' },
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20 },
  sheetTitle: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', marginBottom: 10 },
  note: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginBottom: 12 },
  stars: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginVertical: 12 },
});
