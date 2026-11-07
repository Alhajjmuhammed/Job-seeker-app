/**
 * Post a job (long-term work or a vacancy) - or edit one with ?id=.
 * The post goes to the admin team for review before workers can see it.
 */
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import {
  Btn, Card, Choice, DateField, ErrorBox, Field, Loading, Option, SearchChoice, SectionTitle, Toggle, apiError, isoDate,
} from '../../components/vacancies/ui';

type Form = Record<string, any>;

const blank = (): Form => {
  const today = new Date();
  const inTwoWeeks = new Date(today.getTime() + 14 * 86400000);
  return {
    kind: 'home', company_name: '', category: '', title: '', description: '', requirements: '',
    worker_type_needed: 'any', workers_needed: '1', duration: '3_months',
    start_date: isoDate(inTwoWeeks), closing_date: isoDate(new Date(today.getTime() + 7 * 86400000)),
    salary_amount: '', salary_max: '', pay_period: 'month', pay_day: '',
    city: '', area: '', address: '', working_days: '', working_hours: '',
    live_in: false, food_provided: false, room_provided: false, duties: '', trial_period: '',
    verification_number: '',
  };
};

export default function PostJobScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const editing = !!id;
  const [form, setForm] = useState<Form>(blank());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [categories, setCategories] = useState<Option[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  // the screen stays mounted: load fresh options (and the post being edited) on every visit
  useFocusEffect(useCallback(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setErrors({});
      try {
        const opts = await apiService.getVacancyOptions();
        if (!alive) return;
        setCategories((opts.categories || []).map((c: any) => ({ value: String(c.id), label: c.name })));
        if (id) {
          const v = await apiService.getVacancy(Number(id));
          if (!alive) return;
          const f: Form = blank();
          Object.keys(f).forEach(k => {
            if (v[k] !== undefined && v[k] !== null) f[k] = typeof f[k] === 'boolean' ? !!v[k] : String(v[k]);
          });
          f.category = v.category ? String(v.category) : '';
          setForm(f);
        } else {
          setForm(blank());
        }
        setLoadError(null);
      } catch (e) {
        if (alive) setLoadError(e);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [id, reloadKey]));

  const set = (k: string) => (v: any) => setForm(prev => ({ ...prev, [k]: v }));
  const err = (k: string) => errors[k];

  const submit = async () => {
    const need: Record<string, string> = {};
    if (!form.category) need.category = t('vacancies.required');
    if (!form.title.trim()) need.title = t('vacancies.required');
    if (!form.description.trim()) need.description = t('vacancies.required');
    if (!String(form.salary_amount).trim()) need.salary_amount = t('vacancies.required');
    if (!form.city.trim()) need.city = t('vacancies.required');
    if (!form.verification_number.trim()) need.verification_number = t('vacancies.required');
    if (form.kind === 'business' && !form.company_name.trim()) need.company_name = t('vacancies.required');
    if (Object.keys(need).length) {
      setErrors(need);
      Alert.alert(t('vacancies.checkForm'), t('vacancies.fillRequired'));
      return;
    }
    const payload: Form = { ...form, category: Number(form.category), workers_needed: Number(form.workers_needed) || 1 };
    if (!String(payload.salary_max).trim()) payload.salary_max = null;
    setSaving(true);
    try {
      const v = editing ? await apiService.updateVacancy(Number(id), payload) : await apiService.postVacancy(payload);
      setErrors({});
      Alert.alert(t('vacancies.sentTitle'), t('vacancies.sentText'), [
        { text: 'OK', onPress: () => router.replace(`/(client)/vacancy/${v.id}` as any) },
      ]);
    } catch (e: any) {
      const fieldErrors = e?.response?.data?.errors || {};
      const flat: Record<string, string> = {};
      Object.keys(fieldErrors).forEach(k => { flat[k] = (fieldErrors[k] || [])[0]; });
      setErrors(flat);
      Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed')));
    } finally {
      setSaving(false);
    }
  };

  const kinds: Option[] = [
    { value: 'home', label: t('vacancies.kindHome') },
    { value: 'business', label: t('vacancies.kindBusiness') },
  ];
  const types: Option[] = ['any', 'professional', 'non_academic'].map(v => ({ value: v, label: t(`vacancies.workerTypes.${v}`) }));
  const durations: Option[] = ['one_off', '1_month', '3_months', '6_months', '12_months', 'permanent']
    .map(v => ({ value: v, label: t(`vacancies.durations.${v}`) }));
  const periods: Option[] = ['day', 'week', 'month'].map(v => ({ value: v, label: t(`vacancies.payPeriods.${v}`) }));

  const title = editing ? t('vacancies.editJob') : t('vacancies.postJob');
  if (loading) return <View style={[st.c, { backgroundColor: theme.background }]}><Header title={title} showBack /><Loading /></View>;
  if (loadError) {
    return <View style={[st.c, { backgroundColor: theme.background }]}><Header title={title} showBack />
      <ErrorBox message={apiError(loadError, t('vacancies.loadFailed'))} onRetry={() => setReloadKey(k => k + 1)} /></View>;
  }

  return (
    <View style={[st.c, { backgroundColor: theme.background }]}>
      <Header title={title} showBack />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
          <View style={[st.intro, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Text style={[st.introText, { color: theme.textSecondary }]}>{t('vacancies.postIntro')}</Text>
          </View>

          <Card>
            <SectionTitle>{t('vacancies.aboutYou')}</SectionTitle>
            <Choice label={t('vacancies.whoHiring')} options={kinds} value={form.kind} onChange={set('kind')} />
            {form.kind === 'business' && (
              <Field label={t('vacancies.companyName')} value={form.company_name} onChangeText={set('company_name')} error={err('company_name')} />
            )}
            <Field label={t('vacancies.verificationNumber')} value={form.verification_number} onChangeText={set('verification_number')}
              hint={t('vacancies.verificationHint')} error={err('verification_number')} />
          </Card>

          <Card>
            <SectionTitle>{t('vacancies.theJob')}</SectionTitle>
            <SearchChoice label={t('vacancies.typeOfWork')} options={categories} value={form.category} onChange={set('category')}
              error={err('category')} placeholder={t('vacancies.searchTrade')} />
            <Field label={t('vacancies.jobTitle')} value={form.title} onChangeText={set('title')} maxLength={200}
              placeholder={t('vacancies.jobTitlePlaceholder')} error={err('title')} />
            <Field label={t('vacancies.describe')} value={form.description} onChangeText={set('description')} multiline error={err('description')} />
            <Field label={t('vacancies.requirements')} value={form.requirements} onChangeText={set('requirements')} multiline error={err('requirements')} />
            <Choice label={t('vacancies.workerType')} options={types} value={form.worker_type_needed} onChange={set('worker_type_needed')} />
            <Field label={t('vacancies.howMany')} value={String(form.workers_needed)} onChangeText={set('workers_needed')}
              keyboardType="number-pad" maxLength={3} error={err('workers_needed')} />
          </Card>

          <Card>
            <SectionTitle>{t('vacancies.timeAndPay')}</SectionTitle>
            <Choice label={t('vacancies.howLong')} options={durations} value={form.duration} onChange={set('duration')} />
            <DateField label={t('vacancies.startDate')} value={form.start_date} onChange={set('start_date')} minimumDate={new Date()} error={err('start_date')} />
            <DateField label={t('vacancies.closingDate')} value={form.closing_date} onChange={set('closing_date')} minimumDate={new Date()} error={err('closing_date')} />
            <Field label={t('vacancies.salary')} value={String(form.salary_amount)} onChangeText={set('salary_amount')}
              keyboardType="numeric" error={err('salary_amount')} />
            <Field label={t('vacancies.salaryMax')} value={String(form.salary_max || '')} onChangeText={set('salary_max')}
              keyboardType="numeric" error={err('salary_max')} />
            <Choice label={t('vacancies.paid')} options={periods} value={form.pay_period} onChange={set('pay_period')} />
            <Field label={t('vacancies.payDay')} value={form.pay_day} onChangeText={set('pay_day')} placeholder={t('vacancies.payDayPlaceholder')} />
            <Field label={t('vacancies.workingDays')} value={form.working_days} onChangeText={set('working_days')} placeholder={t('vacancies.workingDaysPlaceholder')} />
            <Field label={t('vacancies.workingHours')} value={form.working_hours} onChangeText={set('working_hours')} placeholder="7:00 - 17:00" />
          </Card>

          <Card>
            <SectionTitle>{t('vacancies.where')}</SectionTitle>
            <Field label={t('vacancies.city')} value={form.city} onChangeText={set('city')} error={err('city')} />
            <Field label={t('vacancies.area')} value={form.area} onChangeText={set('area')} />
            <Field label={t('vacancies.address')} value={form.address} onChangeText={set('address')} hint={t('vacancies.addressHint')} />
          </Card>

          {form.kind === 'home' && (
            <Card>
              <SectionTitle>{t('vacancies.homeDetails')}</SectionTitle>
              <Toggle label={t('vacancies.liveInLong')} value={form.live_in} onChange={set('live_in')} />
              <Toggle label={t('vacancies.foodProvided')} value={form.food_provided} onChange={set('food_provided')} />
              <Toggle label={t('vacancies.roomProvided')} value={form.room_provided} onChange={set('room_provided')} />
              <View style={{ height: 10 }} />
              <Field label={t('vacancies.duties')} value={form.duties} onChangeText={set('duties')} multiline placeholder={t('vacancies.dutiesPlaceholder')} />
              <Field label={t('vacancies.trialPeriod')} value={form.trial_period} onChangeText={set('trial_period')} placeholder={t('vacancies.trialPlaceholder')} />
            </Card>
          )}

          <Btn title={editing ? t('vacancies.sendAgain') : t('vacancies.sendForReview')} icon="send" onPress={submit} busy={saving} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const st = StyleSheet.create({
  c: { flex: 1 },
  intro: { borderRadius: 12, borderWidth: 1, padding: 12, marginBottom: 12 },
  introText: { fontSize: 13, fontFamily: 'Poppins_400Regular', lineHeight: 19 },
});
