/** One job post in a list (worker job board, client "My jobs"). */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { Badge, Tag, salaryText, formatDate } from './ui';

export interface VacancySummary {
  id: number;
  title: string;
  kind: string;
  poster_name: string;
  category_name: string;
  workers_needed: number;
  places_left: number;
  duration_display: string;
  start_date: string;
  closing_date: string;
  salary_amount: string;
  salary_max?: string | null;
  pay_period_display: string;
  city: string;
  area: string;
  worker_type_needed: string;
  worker_type_display: string;
  live_in: boolean;
  food_provided: boolean;
  room_provided: boolean;
  status: string;
  status_display: string;
  is_open: boolean;
  applicant_count?: number;
}

export default function VacancyCard({ v, onPress, showStatus }: { v: VacancySummary; onPress: () => void; showStatus?: boolean }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const where = v.area ? `${v.area}, ${v.city}` : v.city;
  return (
    <TouchableOpacity onPress={onPress} accessibilityRole="button"
      style={[st.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      <View style={st.top}>
        <View style={{ flex: 1 }}>
          <Text style={[st.title, { color: theme.text }]} numberOfLines={2}>{v.title}</Text>
          <Text style={[st.poster, { color: theme.textSecondary }]} numberOfLines={1}>
            {v.poster_name} · {v.category_name}
          </Text>
        </View>
        {showStatus && <Badge status={v.status} label={t(`status.${v.status}`, { defaultValue: v.status_display })} />}
      </View>
      <Text style={[st.salary, { color: theme.primary }]}>{salaryText(v)}</Text>
      <View style={st.tags}>
        <Tag icon="location-outline" label={where} />
        <Tag icon="time-outline" label={v.duration_display} />
        <Tag icon="people-outline" label={t('vacancies.placesLeft', { count: v.places_left, total: v.workers_needed })} />
        {v.worker_type_needed !== 'any' && <Tag icon="school-outline" label={v.worker_type_display} />}
        {v.live_in && <Tag icon="home-outline" label={t('vacancies.liveIn')} />}
        {v.food_provided && <Tag icon="restaurant-outline" label={t('vacancies.food')} />}
        {v.room_provided && <Tag icon="bed-outline" label={t('vacancies.room')} />}
      </View>
      <Text style={[st.foot, { color: theme.textSecondary }]}>
        {t('vacancies.closesOn', { date: formatDate(v.closing_date) })}
        {typeof v.applicant_count === 'number' ? ` · ${t('vacancies.applicantCount', { count: v.applicant_count })}` : ''}
      </Text>
    </TouchableOpacity>
  );
}

const st = StyleSheet.create({
  card: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  top: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  title: { fontSize: 16, fontFamily: 'Poppins_600SemiBold' },
  poster: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 2 },
  salary: { fontSize: 15, fontFamily: 'Poppins_700Bold', marginTop: 8 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  foot: { fontSize: 12, fontFamily: 'Poppins_400Regular', marginTop: 10 },
});
