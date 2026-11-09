import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  StyleProp,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../contexts/ThemeContext';
import { SUPPORTED_LANGUAGES, changeLanguage } from '../services/i18n';

interface LanguagePickerProps {
  /** Style for the tappable settings row (lets each settings screen keep its own look). */
  rowStyle?: StyleProp<ViewStyle>;
  /** Style for the "Language" label. */
  labelStyle?: StyleProp<TextStyle>;
  /** Style for the leading language icon. */
  iconStyle?: StyleProp<TextStyle>;
  iconSize?: number;
}

/**
 * Settings row + bottom-sheet modal for choosing the app language.
 * changeLanguage() saves the choice in AsyncStorage and switches i18next,
 * so the choice survives app restarts. Shared by the worker and client
 * settings screens so they behave the same.
 */
export default function LanguagePicker({ rowStyle, labelStyle, iconStyle, iconSize = 24 }: LanguagePickerProps) {
  const { t, i18n } = useTranslation();
  const { theme } = useTheme();
  const [visible, setVisible] = useState(false);

  const current = SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language);

  const handleSelectLanguage = async (code: string) => {
    setVisible(false);
    await changeLanguage(code);
  };

  return (
    <>
      <Modal
        visible={visible}
        transparent
        animationType="slide"
        onRequestClose={() => setVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContainer, { backgroundColor: theme.surface }]}>
            <Text style={[styles.modalTitle, { color: theme.text }]}>{t('settings.languageSelect')}</Text>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <TouchableOpacity
                key={lang.code}
                style={[
                  styles.langOption,
                  { borderColor: theme.border },
                  i18n.language === lang.code && { borderColor: theme.primary, backgroundColor: theme.primary + '15' },
                ]}
                onPress={() => handleSelectLanguage(lang.code)}
              >
                <Text style={styles.langFlag}>{lang.flag}</Text>
                <View style={styles.langInfo}>
                  <Text style={[styles.langName, { color: theme.text }]}>{lang.name}</Text>
                  <Text style={[styles.langNative, { color: theme.textSecondary }]}>{lang.nativeName}</Text>
                </View>
                {i18n.language === lang.code && (
                  <Ionicons name="checkmark-circle" size={22} color={theme.primary} />
                )}
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              style={[styles.modalCancel, { borderColor: theme.border }]}
              onPress={() => setVisible(false)}
            >
              <Text style={[styles.modalCancelText, { color: theme.textSecondary }]}>{t('common.cancel')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <TouchableOpacity style={rowStyle ?? styles.settingRow} onPress={() => setVisible(true)}>
        <View style={styles.settingLeft}>
          <Ionicons name="language-outline" size={iconSize} color={theme.primary} style={iconStyle} />
          <Text style={labelStyle ?? [styles.settingText, { color: theme.text }]}>{t('settings.language')}</Text>
        </View>
        <View style={styles.settingRight}>
          <Text style={[styles.settingValue, { color: theme.textSecondary }]}>
            {current?.flag}{' '}
            {current?.name ?? 'English'}
          </Text>
          <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
        </View>
      </TouchableOpacity>
    </>
  );
}

const styles = StyleSheet.create({
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  settingRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  settingText: {
    fontSize: 15,
    fontFamily: 'Poppins_500Medium',
  },
  settingValue: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 36,
  },
  modalTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  langOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    marginBottom: 10,
  },
  langFlag: {
    fontSize: 26,
  },
  langInfo: {
    flex: 1,
  },
  langName: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
  },
  langNative: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  modalCancel: {
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    alignItems: 'center',
    marginTop: 4,
  },
  modalCancelText: {
    fontSize: 15,
    fontFamily: 'Poppins_500Medium',
  },
});
