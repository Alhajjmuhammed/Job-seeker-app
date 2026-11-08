/**
 * Turn any API error into ONE sentence a person can read.
 *
 * The server answers {error: "..."} - but older servers (and some paths) sent
 * {error: {code, message, details}}, {detail: "..."} or {field: ["..."]}. Screens show
 * error.response.data.error in Alert.alert; an object there crashed Android (red screen),
 * showed nothing on iOS, and "[object Object]" on login.
 */
export function readable(value: any): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const text = readable(item);
      if (text) return text;
    }
    return '';
  }
  if (typeof value === 'object') {
    for (const key of ['message', 'detail', 'error', 'non_field_errors']) {
      if (key in value) {
        const text = readable(value[key]);
        if (text && text !== 'Error') return text;
      }
    }
    if (value.details) {
      const text = readable(value.details);
      if (text) return text;
    }
    for (const key of Object.keys(value)) {
      if (key === 'code') continue;
      const text = readable(value[key]);
      if (text) return `${key.replace(/_/g, ' ')}: ${text}`;
    }
  }
  return '';
}

/** Make response.data.error a plain string (called once for every failed request). */
export function normalizeErrorBody(data: any): any {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return data;
  if (data.error && typeof data.error !== 'string') {
    if (data.error && typeof data.error === 'object' && data.error.code && !data.code) data.code = data.error.code;
    data.error = readable(data.error) || 'Something went wrong. Please try again.';
  } else if (!data.error && typeof data.detail === 'string') {
    data.error = data.detail;
  }
  return data;
}

/** The message to show for a failed call, or the fallback. */
export function errorText(e: any, fallback: string): string {
  const data = e?.response?.data;
  if (!data) {
    return e?.message === 'Network Error'
      ? 'No internet connection. Please check your connection and try again.'
      : fallback;
  }
  if (typeof data === 'string') return fallback; // an HTML error page
  return readable(normalizeErrorBody(data).error) || readable(data) || fallback;
}
