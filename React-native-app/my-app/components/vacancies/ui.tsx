/**
 * Small building blocks shared by the job post (vacancy) screens - one look,
 * theme colours everywhere so dark mode works.
 */
import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Platform, Switch,
  TextInputProps, ViewStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
// @ts-ignore - package is installed; types resolve at build time
import DateTimePicker from '@react-native-community/datetimepicker';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { errorText } from '../../utils/apiError';

export type Option = { value: string; label: string };

/** Server status -> colour */
export function statusTone(status: string): { bg: string; fg: string } {
  switch (status) {
    case 'published': case 'active': case 'hired': return { bg: '#D1FAE5', fg: '#065F46' };
    case 'review': case 'applied': return { bg: '#DBEAFE', fg: '#1E40AF' };
    case 'shortlisted': case 'renewed': return { bg: '#EDE9FE', fg: '#5B21B6' };
    case 'changes': return { bg: '#FEF3C7', fg: '#92400E' };
    case 'rejected': case 'not_selected': case 'ended_early': case 'ended': return { bg: '#FEE2E2', fg: '#991B1B' };
    default: return { bg: '#E5E7EB', fg: '#374151' }; // filled, closed, finished, withdrawn
  }
}

export function Badge({ status, label }: { status: string; label: string }) {
  const tone = statusTone(status);
  return (
    <View style={[s.badge, { backgroundColor: tone.bg }]}>
      <Text style={[s.badgeText, { color: tone.fg }]}>{label}</Text>
    </View>
  );
}

export function Tag({ icon, label }: { icon: any; label: string }) {
  const { theme } = useTheme();
  return (
    <View style={[s.tag, { backgroundColor: theme.background, borderColor: theme.border }]}>
      <Ionicons name={icon} size={12} color={theme.textSecondary} />
      <Text style={[s.tagText, { color: theme.textSecondary }]}>{label}</Text>
    </View>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  const { theme } = useTheme();
  return <View style={[s.card, { backgroundColor: theme.surface, borderColor: theme.border }, style]}>{children}</View>;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  return <Text style={[s.section, { color: theme.text }]}>{children}</Text>;
}

export function Row({ label, value }: { label: string; value?: string | number | null }) {
  const { theme } = useTheme();
  if (value === undefined || value === null || value === '') return null;
  return (
    <View style={s.row}>
      <Text style={[s.rowLabel, { color: theme.textSecondary }]}>{label}</Text>
      <Text style={[s.rowValue, { color: theme.text }]}>{String(value)}</Text>
    </View>
  );
}

export function Field({ label, error, hint, ...props }: TextInputProps & { label: string; error?: string; hint?: string }) {
  const { theme } = useTheme();
  return (
    <View style={s.field}>
      <Text style={[s.label, { color: theme.text }]}>{label}</Text>
      <TextInput
        placeholderTextColor={theme.textSecondary}
        {...props}
        style={[s.input, { color: theme.text, backgroundColor: theme.background, borderColor: error ? theme.error : theme.border },
          props.multiline ? { minHeight: 84, textAlignVertical: 'top' } : null]}
      />
      {!!hint && !error && <Text style={[s.hint, { color: theme.textSecondary }]}>{hint}</Text>}
      {!!error && <Text style={[s.hint, { color: theme.error }]}>{error}</Text>}
    </View>
  );
}

/** Tap-to-choose list of options (instead of a native picker: works the same everywhere). */
export function Choice({ label, options, value, onChange, error }: {
  label?: string; options: Option[]; value: string; onChange: (v: string) => void; error?: string;
}) {
  const { theme } = useTheme();
  return (
    <View style={s.field}>
      {!!label && <Text style={[s.label, { color: theme.text }]}>{label}</Text>}
      <View style={s.chips}>
        {options.map(o => {
          const on = o.value === value;
          return (
            <TouchableOpacity key={o.value} onPress={() => onChange(o.value)} accessibilityState={{ selected: on }}
              style={[s.chip, { borderColor: on ? theme.primary : theme.border, backgroundColor: on ? theme.primary : theme.background }]}>
              <Text style={[s.chipText, { color: on ? '#FFFFFF' : theme.text }]}>{o.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
      {!!error && <Text style={[s.hint, { color: theme.error }]}>{error}</Text>}
    </View>
  );
}

/** Choice for long lists (200+ trades): type to filter, shows up to 12 matches. */
export function SearchChoice({ label, options, value, onChange, error, placeholder }: {
  label: string; options: Option[]; value: string; onChange: (v: string) => void; error?: string; placeholder?: string;
}) {
  const { theme } = useTheme();
  const [q, setQ] = useState('');
  const chosen = options.find(o => o.value === value);
  const needle = q.trim().toLowerCase();
  const shown = options.filter(o => o.value !== value && (!needle || o.label.toLowerCase().includes(needle))).slice(0, 12);
  return (
    <View style={s.field}>
      <Text style={[s.label, { color: theme.text }]}>{label}</Text>
      {!!chosen && (
        <View style={[s.chips, { marginBottom: 8 }]}>
          <View style={[s.chip, { borderColor: theme.primary, backgroundColor: theme.primary, flexDirection: 'row', alignItems: 'center', gap: 6 }]}>
            <Ionicons name="checkmark" size={14} color="#FFFFFF" />
            <Text style={[s.chipText, { color: '#FFFFFF' }]}>{chosen.label}</Text>
          </View>
        </View>
      )}
      <TextInput value={q} onChangeText={setQ} placeholder={placeholder} placeholderTextColor={theme.textSecondary}
        style={[s.input, { color: theme.text, backgroundColor: theme.background, borderColor: error ? theme.error : theme.border, marginBottom: 8 }]} />
      <View style={s.chips}>
        {shown.map(o => (
          <TouchableOpacity key={o.value} onPress={() => { onChange(o.value); setQ(''); }}
            style={[s.chip, { borderColor: theme.border, backgroundColor: theme.background }]}>
            <Text style={[s.chipText, { color: theme.text }]}>{o.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      {!!error && <Text style={[s.hint, { color: theme.error }]}>{error}</Text>}
    </View>
  );
}

export function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  const { theme } = useTheme();
  return (
    <View style={[s.toggle, { borderColor: theme.border }]}>
      <Text style={[s.toggleText, { color: theme.text }]}>{label}</Text>
      <Switch value={value} onValueChange={onChange} trackColor={{ true: theme.primaryLight, false: theme.border }}
        thumbColor={value ? theme.primary : '#9CA3AF'} />
    </View>
  );
}

export const isoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export const parseIso = (v?: string | null) => {
  if (!v) return new Date();
  const [y, m, d] = v.split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
};

export function DateField({ label, value, onChange, error, minimumDate }: {
  label: string; value: string; onChange: (v: string) => void; error?: string; minimumDate?: Date;
}) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  return (
    <View style={s.field}>
      <Text style={[s.label, { color: theme.text }]}>{label}</Text>
      <TouchableOpacity onPress={() => setOpen(true)}
        style={[s.input, s.dateBtn, { backgroundColor: theme.background, borderColor: error ? theme.error : theme.border }]}>
        <Ionicons name="calendar-outline" size={18} color={theme.textSecondary} />
        <Text style={{ color: value ? theme.text : theme.textSecondary, fontFamily: 'Poppins_400Regular' }}>
          {value ? formatDate(value) : '—'}
        </Text>
      </TouchableOpacity>
      {!!error && <Text style={[s.hint, { color: theme.error }]}>{error}</Text>}
      {open && (
        <DateTimePicker
          value={parseIso(value)}
          mode="date"
          minimumDate={minimumDate}
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(_e: any, d?: Date) => { setOpen(false); if (d) onChange(isoDate(d)); }}
        />
      )}
    </View>
  );
}

export function Btn({ title, onPress, kind = 'primary', icon, busy, disabled, style }: {
  title: string; onPress: () => void; kind?: 'primary' | 'outline' | 'danger' | 'ghost'; icon?: any;
  busy?: boolean; disabled?: boolean; style?: ViewStyle;
}) {
  const { theme } = useTheme();
  const bg = kind === 'primary' ? theme.primary : kind === 'danger' ? theme.error : 'transparent';
  const fg = kind === 'primary' || kind === 'danger' ? '#FFFFFF' : kind === 'outline' ? theme.primary : theme.textSecondary;
  const off = disabled || busy;
  return (
    <TouchableOpacity onPress={onPress} disabled={off} accessibilityRole="button"
      style={[s.btn, { backgroundColor: bg, borderColor: kind === 'outline' ? theme.primary : bg, opacity: off ? 0.6 : 1 }, style]}>
      {busy ? <ActivityIndicator size="small" color={fg} /> : (
        <>
          {!!icon && <Ionicons name={icon} size={17} color={fg} />}
          <Text style={[s.btnText, { color: fg }]}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

export function Loading() {
  const { theme } = useTheme();
  return <View style={s.center}><ActivityIndicator size="large" color={theme.primary} /></View>;
}

export function Empty({ icon = 'briefcase-outline', title, text, action }: {
  icon?: any; title: string; text?: string; action?: React.ReactNode;
}) {
  const { theme } = useTheme();
  return (
    <View style={s.empty}>
      <Ionicons name={icon} size={48} color={theme.textSecondary} />
      <Text style={[s.emptyTitle, { color: theme.text }]}>{title}</Text>
      {!!text && <Text style={[s.emptyText, { color: theme.textSecondary }]}>{text}</Text>}
      {action}
    </View>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <Empty icon="cloud-offline-outline" title={t('common.error')} text={message}
      action={onRetry ? <Btn title={t('common.retry')} kind="outline" onPress={onRetry} style={{ marginTop: 14 }} /> : undefined} />
  );
}

export const formatDate = (v?: string | null) => {
  if (!v) return '';
  const d = parseIso(v.slice(0, 10));
  return d.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
};

export const formatMoney = (amount?: string | null) => {
  if (amount === undefined || amount === null || amount === '') return '';
  const n = Number(amount);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : String(amount);
};

/** "TSh 300,000 – 400,000 per month" */
export const salaryText = (v: { salary_amount?: string | null; salary_max?: string | null; pay_period_display?: string }) => {
  const low = formatMoney(v.salary_amount);
  const high = v.salary_max ? ` – ${formatMoney(v.salary_max)}` : '';
  return `TSh ${low}${high} ${v.pay_period_display || ''}`.trim();
};

/** First message from an API error ({error} / {errors} / {detail}). */
export const apiError = (e: any, fallback: string) => errorText(e, fallback);

const s = StyleSheet.create({
  badge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 12, alignSelf: 'flex-start' },
  badgeText: { fontSize: 11, fontFamily: 'Poppins_600SemiBold' },
  tag: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10, borderWidth: 1 },
  tagText: { fontSize: 11, fontFamily: 'Poppins_500Medium' },
  card: { borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1 },
  section: { fontSize: 16, fontFamily: 'Poppins_600SemiBold', marginBottom: 10, marginTop: 6 },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, paddingVertical: 5 },
  rowLabel: { fontSize: 13, fontFamily: 'Poppins_400Regular', flexShrink: 0 },
  rowValue: { fontSize: 13, fontFamily: 'Poppins_500Medium', flex: 1, textAlign: 'right' },
  field: { marginBottom: 14 },
  label: { fontSize: 13, fontFamily: 'Poppins_600SemiBold', marginBottom: 6 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, fontFamily: 'Poppins_400Regular' },
  hint: { fontSize: 12, marginTop: 4, fontFamily: 'Poppins_400Regular' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 8 },
  chipText: { fontSize: 13, fontFamily: 'Poppins_500Medium' },
  toggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, marginBottom: 6 },
  toggleText: { fontSize: 14, fontFamily: 'Poppins_400Regular', flex: 1, marginRight: 10 },
  dateBtn: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  btn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderRadius: 12, borderWidth: 1, paddingVertical: 12, paddingHorizontal: 16 },
  btnText: { fontSize: 14, fontFamily: 'Poppins_600SemiBold' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 60 },
  empty: { alignItems: 'center', paddingVertical: 50, paddingHorizontal: 24 },
  emptyTitle: { fontSize: 17, fontFamily: 'Poppins_600SemiBold', marginTop: 12, textAlign: 'center' },
  emptyText: { fontSize: 14, fontFamily: 'Poppins_400Regular', marginTop: 6, textAlign: 'center' },
});
