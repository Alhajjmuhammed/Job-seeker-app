/**
 * "Export My Data": the server returns the export right away
 * (GET /api/v1/gdpr/export/ - nothing is emailed), so hand it to the
 * phone's share sheet where the user can save it to Files or send it on.
 */
import { Alert, Share } from 'react-native';
import i18next from 'i18next';
import apiService from './api';

export async function exportMyData(setBusy?: (busy: boolean) => void) {
  const t = i18next.t.bind(i18next);
  try {
    setBusy?.(true);
    const data = await apiService.exportUserData();
    await Share.share({
      title: t('privacy.exportData'),
      message: JSON.stringify(data, null, 2),
    });
  } catch (error: any) {
    Alert.alert(t('common.error'), error?.response?.data?.error || t('privacy.exportFailed'));
  } finally {
    setBusy?.(false);
  }
}

export function confirmExportMyData(setBusy?: (busy: boolean) => void) {
  const t = i18next.t.bind(i18next);
  Alert.alert(t('privacy.exportData'), t('privacy.exportExplain'), [
    { text: t('common.cancel'), style: 'cancel' },
    { text: t('privacy.exportNow'), onPress: () => exportMyData(setBusy) },
  ]);
}
