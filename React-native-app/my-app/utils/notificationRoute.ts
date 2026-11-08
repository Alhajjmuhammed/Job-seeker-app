/**
 * Where a tapped notification should open in the app.
 *
 * Shared by the client and worker notification lists and by the push
 * notification tap handler, so all three agree. It reads what the server
 * really stores (worker_connect.Notification: `notification_type` plus the
 * `extra_data` dict) and mirrors the website's Notification.target_url.
 *
 * Pure: no navigation, no side effects. Returns an Expo Router href, or null
 * when there is nothing specific to open (callers decide the fallback).
 * Never returns a worker screen for a client or a client screen for a worker.
 */

export type NotificationRole = 'worker' | 'client' | string | null | undefined;

export interface NotificationRouteInput {
  /** notification_type from the API (or `type` in a push payload) */
  type?: string | null;
  /** extra_data from the API (or the push payload's data) */
  data?: Record<string, any> | string | null;
  role: NotificationRole;
}

/** Ids may arrive as numbers (API) or strings (push payloads). */
function id(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const s = String(value).trim();
  return s && s !== 'null' && s !== 'undefined' ? encodeURIComponent(s) : null;
}

function toData(data: NotificationRouteInput['data']): Record<string, any> {
  if (!data) return {};
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }
  return typeof data === 'object' ? data : {};
}

const JOB_TYPES = ['job_assigned', 'job_accepted', 'job_rejected', 'job_application'];
const MESSAGE_TYPES = ['message_received', 'new_message', 'message'];

export function routeForNotification({ type, data, role }: NotificationRouteInput): string | null {
  if (role !== 'worker' && role !== 'client') return null; // admins have no app area
  const d = toData(data);
  const t = String(type || '');
  const area = role === 'worker' ? '/(worker)' : '/(client)';

  // Messages: straight into the chat with whoever wrote, else the inbox.
  if (MESSAGE_TYPES.includes(t)) {
    const sender = id(d.sender_id ?? d.user_id);
    return sender ? `${area}/conversation/${sender}` : `${area}/messages`;
  }

  // Document review result (admin_panel/verification_views.py).
  if (d.action === 'open_documents' || t === 'document_verified') {
    return role === 'worker' ? '/(worker)/documents' : null;
  }
  // "Please save your location" broadcast.
  if (d.action === 'save_location') {
    return role === 'worker' ? '/(worker)/profile-edit' : null;
  }

  // Job posts (jobs/vacancy_service.py): a contract first, then the job post.
  const contract = id(d.contract_id);
  if (contract) return `${area}/contract/${contract}`;
  const vacancy = id(d.vacancy_id);
  if (vacancy) return `${area}/vacancy/${vacancy}`;

  // Direct hire (bookings made straight with a worker).
  const directHire = id(d.direct_hire_id);
  if (directHire) return `${area}/direct-hire/${directHire}`;

  // Service requests (admin-assigned bookings).
  const requestId = id(d.service_request_id ?? d.request_id);
  const assignment = id(d.assignment_id);
  if (role === 'worker') {
    if (t === 'job_completed' || t === 'payment_received') return '/(worker)/earnings';
    if (assignment) return `/(worker)/service-assignment/${assignment}`;
    if (requestId) return '/(worker)/jobs';
    const job = id(d.job_id); // legacy job requests
    if (job) return `/(worker)/job/${job}`;
    if (JOB_TYPES.includes(t)) return '/(worker)/jobs';
    return null;
  }
  if (requestId) return `/(client)/service-request/${requestId}`;
  if (JOB_TYPES.includes(t)) return '/(client)/my-requests';
  return null;
}
