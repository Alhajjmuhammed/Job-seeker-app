/** "My direct bookings" - the same list for the client (who booked) and the worker (who was booked). */
import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../Header';
import apiService from '../../services/api';
import { usePaged } from '../vacancies/usePaged';
import { Badge, Choice, Empty, ErrorBox, Loading, apiError, formatMoney } from '../vacancies/ui';
import { DirectHire, durationText, hireTone, startText } from './common';

const TABS = [
  { value: 'pending', key: 'pending' },
  { value: 'accepted', key: 'accepted' },
  { value: 'completed', key: 'completed' },
  { value: 'rejected,cancelled', key: 'closed' },
];

export default function DirectHireList({ group }: { group: '(client)' | '(worker)' }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [status, setStatus] = useState('pending');
  const role = group === '(client)' ? 'client' : 'worker';
  const list = usePaged<DirectHire>((page) => apiService.getDirectHires({ status, role, page }), [status]);
  const isClient = group === '(client)';

  return (
    <View style={[st.container, { backgroundColor: theme.background }]}>
      <Header title={t('directHire.myBookings')} showBack />
      <View style={st.filters}>
        <Choice options={TABS.map(x => ({ value: x.value, label: t(`directHire.tabs.${x.key}`) }))}
          value={status} onChange={setStatus} />
      </View>
      {list.loading ? <Loading /> : list.error ? (
        <ErrorBox message={apiError(list.error, t('directHire.loadFailed'))} onRetry={list.reload} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={h => String(h.id)}
          contentContainerStyle={{ padding: 16, paddingTop: 4 }}
          refreshControl={<RefreshControl refreshing={list.refreshing} onRefresh={list.refresh} colors={[theme.primary]} />}
          onEndReached={list.loadMore}
          onEndReachedThreshold={0.4}
          ListFooterComponent={list.loadingMore ? <ActivityIndicator color={theme.primary} style={{ margin: 16 }} /> : null}
          ListEmptyComponent={<Empty icon="person-add-outline"
            title={isClient ? t('directHire.emptyClient') : t('directHire.emptyWorker')}
            text={isClient ? t('directHire.emptyClientText') : t('directHire.emptyWorkerText')} />}
          renderItem={({ item: h }) => (
            <TouchableOpacity onPress={() => router.push(`/${group}/direct-hire/${h.id}` as any)}
              style={[st.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <View style={st.top}>
                <Text style={[st.title, { color: theme.text }]} numberOfLines={2}>{h.title}</Text>
                <Badge status={hireTone(h.status)} label={h.status_display} />
              </View>
              <Text style={[st.sub, { color: theme.textSecondary }]}>
                {isClient ? h.worker.full_name : h.client.full_name}
              </Text>
              <Text style={[st.money, { color: theme.primary }]}>TSh {formatMoney(h.total_amount)}</Text>
              <View style={st.meta}>
                <Ionicons name="time-outline" size={13} color={theme.textSecondary} />
                <Text style={[st.sub, { color: theme.textSecondary, marginTop: 0 }]}>
                  {startText(h.start_datetime)} · {durationText(t, h)}
                </Text>
              </View>
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
  money: { fontSize: 14, fontFamily: 'Poppins_700Bold', marginTop: 6 },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 4 },
});
