/** "Report a problem" for a job post or a contract - goes to the admin team. */
import React, { useState } from 'react';
import { Modal, View, Text, StyleSheet, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { Btn, Choice, Field, apiError } from './ui';

const TYPES = ['fraud', 'safety_concern', 'harassment', 'inappropriate_content', 'spam', 'other'];

export default function ReportSheet({ visible, onClose, send }: {
  visible: boolean; onClose: () => void;
  send: (reportType: string, description: string) => Promise<any>;
}) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [type, setType] = useState('other');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!text.trim()) {
      Alert.alert(t('vacancies.report'), t('vacancies.reportNeedText'));
      return;
    }
    setBusy(true);
    try {
      await send(type, text.trim());
      setText('');
      onClose();
      Alert.alert(t('vacancies.report'), t('vacancies.reportThanks'));
    } catch (e: any) {
      Alert.alert(t('common.error'), apiError(e, t('vacancies.actionFailed')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={st.backdrop}>
        <View style={[st.sheet, { backgroundColor: theme.surface }]}>
          <ScrollView keyboardShouldPersistTaps="handled">
            <Text style={[st.title, { color: theme.text }]}>{t('vacancies.reportTitle')}</Text>
            <Choice label={t('vacancies.reportWhat')} value={type} onChange={setType}
              options={TYPES.map(v => ({ value: v, label: t(`vacancies.reportTypes.${v}`) }))} />
            <Field label={t('vacancies.reportMore')} value={text} onChangeText={setText} multiline maxLength={2000} />
            <View style={st.actions}>
              <Btn title={t('common.cancel')} kind="ghost" onPress={onClose} style={{ flex: 1 }} />
              <Btn title={t('vacancies.sendReport')} kind="danger" onPress={submit} busy={busy} style={{ flex: 1 }} />
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const st = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '85%' },
  title: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', marginBottom: 14 },
  actions: { flexDirection: 'row', gap: 10, marginTop: 6 },
});
