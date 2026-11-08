/** Shared types and small helpers for the direct hire screens. */
import { formatMoney } from '../vacancies/ui';

export interface DirectHire {
  id: number;
  my_role: 'client' | 'worker' | null;
  status: 'pending' | 'accepted' | 'rejected' | 'completed' | 'cancelled';
  status_display: string;
  title: string;
  description: string;
  location: string;
  location_hidden: boolean;
  duration_type: 'hours' | 'days';
  duration_value: number;
  start_datetime: string | null;
  offered_rate: string;
  total_amount: string;
  worker: { id: number; user_id: number; full_name: string; rating: number; profile_picture: string | null; phone: string };
  client: { id: number; full_name: string; phone: string };
  worker_response_message: string;
  responded_at: string | null;
  completed_at: string | null;
  client_rating: number | null;
  client_feedback: string;
  created_at: string | null;
  worker_busy: boolean;
  can_accept: boolean;
  can_decline: boolean;
  can_complete: boolean;
  can_cancel: boolean;
  can_chat: boolean;
}

type T = (key: string, opts?: any) => string;

/** Booking status -> one of the colours statusTone() in vacancies/ui knows. */
export function hireTone(status: string): string {
  switch (status) {
    case 'pending': return 'review';
    case 'accepted': return 'active';
    case 'completed': return 'hired';
    case 'rejected': return 'rejected';
    case 'cancelled': return 'ended';
    default: return status;
  }
}

export function durationText(t: T, h: { duration_type: string; duration_value: number }) {
  return h.duration_type === 'days'
    ? t('directHire.durationDays', { count: h.duration_value })
    : t('directHire.durationHours', { count: h.duration_value });
}

export function rateText(t: T, h: { duration_type: string; offered_rate: string }) {
  const rate = formatMoney(h.offered_rate);
  return h.duration_type === 'days' ? t('directHire.rateDay', { rate }) : t('directHire.rateHour', { rate });
}

export function startText(iso?: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString([], { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
