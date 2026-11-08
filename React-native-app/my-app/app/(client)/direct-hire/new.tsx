/**
 * Client books one worker directly: what, where, how long, when and the rate.
 * The rate is per hour or per day; the total is rate x how long (the server
 * works it out the same way). The worker answers; address and phone numbers
 * are shared only after they accept.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, TouchableOpacity, Platform, KeyboardAvoidingView } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
// @ts-ignore - package is installed; types resolve at build time
import DateTimePicker from '@react-native-community/datetimepicker';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../../contexts/ThemeContext';
import Header from '../../../components/Header';
import apiService from '../../../services/api';
import { Btn, Card, Choice, DateField, Empty, Field, apiError, formatMoney, isoDate } from '../../../components/vacancies/ui';
import { durationText } from '../../../components/directHire/common';

const pad = (n: number) => String(n).padStart(2, '0');

function tomorrowAt8() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(8, 0, 0, 0);
  return d;
}

export default function NewDirectHireScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const params = useLocalSearchParams<{ workerId?: string; workerName?: string }>();
  const workerId = Number(params.workerId);

  const start0 = useMemo(tomorrowAt8, []);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [durationType, setDurationType] = useState<'hours' | 'days'>('hours');
  const [durationValue, setDurationValue] = useState('');
  const [date, setDate] = useState(isoDate(start0));
  const [time, setTime] = useState(`${pad(start0.getHours())}:${pad(start0.getMinutes())}`);
  const [timeOpen, setTimeOpen] = useState(false);
  const [rate, setRate] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  // hidden tab screens stay mounted: start a clean form for every worker
  useEffect(() => {
    const d = tomorrowAt8();
    setTitle(''); setDescription(''); setLocation(''); setDurationType('hours'); setDurationValue('');
    setDate(isoDate(d)); setTime(`${pad(d.getHours())}:${pad(d.getMinutes())}`); setRate(''); setErrors({});
  }, [workerId]);

  const count = parseInt(durationValue, 10);
  const rateNum = Number(rate.replace(/,/g, ''));
  const total = count >= 1 && rateNum > 0 ? count * rateNum : null;

  const startDate = () => {
    const [y, m, d] = date.split('-').map(Number);
    const [hh, mm] = time.split(':').map(Number);
    return new Date(y, (m || 1) - 1, d || 1, hh || 0, mm || 0, 0, 0);
  };

  if (!workerId) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.background }}>
        <Header title={t('directHire.newTitle')} showBack />
        <Empty icon="person-outline" title={t('directHire.noWorker')} />
      </View>
    );
  }

  const validate = () => {
    const e: Record<string, string> = {};
    if (!title.trim()) e.title = t('directHire.required');
    if (!description.trim()) e.description = t('directHire.required');
    if (!location.trim()) e.location = t('directHire.required');
    if (!(count >= 1)) e.duration = t('directHire.durationMin');
    if (!(rateNum > 0)) e.rate = t('directHire.rateMin');
    if (startDate().getTime() < Date.now() - 10 * 60 * 1000) e.start = t('directHire.startPast');
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async () => {
    if (!validate()) return;
    setBusy(true);
    try {
      const hire = await apiService.createDirectHire({
        worker_id: workerId,
        title: title.trim(),
        description: description.trim(),
        location: location.trim(),
        duration_type: durationType,
        duration_value: count,
        start_datetime: startDate().toISOString(),
        offered_rate: String(rateNum),
      });
      Alert.alert(t('common.success'), t('directHire.sent'));
      router.replace(`/(client)/direct-hire/${hire.id}` as any);
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('directHire.sendFailed')));
    } finally {
      setBusy(false);
    }
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <Header title={t('directHire.newTitle')} showBack />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
          {!!params.workerName && (
            <Text style={[st.who, { color: theme.text }]}>{t('directHire.bookingWith', { name: params.workerName })}</Text>
          )}
          <Text style={[st.intro, { color: theme.textSecondary }]}>{t('directHire.intro')}</Text>

          <Card>
            <Field label={t('directHire.title')} placeholder={t('directHire.titlePlaceholder')} value={title}
              onChangeText={setTitle} maxLength={200} error={errors.title} />
            <Field label={t('directHire.description')} placeholder={t('directHire.descriptionPlaceholder')}
              value={description} onChangeText={setDescription} multiline maxLength={3000} error={errors.description} />
            <Field label={t('directHire.location')} placeholder={t('directHire.locationPlaceholder')} value={location}
              onChangeText={setLocation} maxLength={255} error={errors.location} />
          </Card>

          <Card>
            <Choice label={t('directHire.durationType')} value={durationType}
              onChange={(v) => setDurationType(v as 'hours' | 'days')}
              options={[{ value: 'hours', label: t('directHire.perHour') }, { value: 'days', label: t('directHire.perDay') }]} />
            <Field label={durationType === 'days' ? t('directHire.daysCount') : t('directHire.hoursCount')}
              value={durationValue} onChangeText={(v) => setDurationValue(v.replace(/[^0-9]/g, ''))}
              keyboardType="number-pad" maxLength={4} error={errors.duration} />
            <Field label={durationType === 'days' ? t('directHire.ratePerDay') : t('directHire.ratePerHour')}
              value={rate} onChangeText={(v) => setRate(v.replace(/[^0-9.]/g, ''))}
              keyboardType="decimal-pad" maxLength={10} error={errors.rate} />

            <View style={[st.total, { backgroundColor: theme.background, borderColor: theme.border }]}>
              <Text style={[st.totalLabel, { color: theme.textSecondary }]}>{t('directHire.total')}</Text>
              <Text style={[st.totalValue, { color: theme.primary }]}>
                {total !== null
                  ? t('directHire.totalLine', {
                      rate: formatMoney(String(rateNum)),
                      duration: durationText(t, { duration_type: durationType, duration_value: count }),
                      total: formatMoney(String(total)),
                    })
                  : '—'}
              </Text>
            </View>
          </Card>

          <Card>
            <DateField label={t('directHire.startDate')} value={date} onChange={setDate} minimumDate={today} error={errors.start} />
            <Text style={[st.label, { color: theme.text }]}>{t('directHire.startTime')}</Text>
            <TouchableOpacity onPress={() => setTimeOpen(true)}
              style={[st.timeBtn, { backgroundColor: theme.background, borderColor: errors.start ? theme.error : theme.border }]}>
              <Ionicons name="time-outline" size={18} color={theme.textSecondary} />
              <Text style={{ color: theme.text, fontFamily: 'Poppins_400Regular' }}>{time}</Text>
            </TouchableOpacity>
            {timeOpen && (
              <DateTimePicker
                value={startDate()}
                mode="time"
                is24Hour
                display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                onChange={(_e: any, d?: Date) => {
                  setTimeOpen(false);
                  if (d) setTime(`${pad(d.getHours())}:${pad(d.getMinutes())}`);
                }}
              />
            )}
          </Card>

          <Btn title={t('directHire.send')} icon="paper-plane-outline" busy={busy} onPress={submit} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const st = StyleSheet.create({
  who: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', marginBottom: 4 },
  intro: { fontSize: 13, fontFamily: 'Poppins_400Regular', marginBottom: 14, lineHeight: 19 },
  label: { fontSize: 13, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  timeBtn: { flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, marginBottom: 6 },
  total: { borderWidth: 1, borderRadius: 10, padding: 12 },
  totalLabel: { fontSize: 12, fontFamily: 'Poppins_500Medium' },
  totalValue: { fontSize: 15, fontFamily: 'Poppins_700Bold', marginTop: 2 },
});
