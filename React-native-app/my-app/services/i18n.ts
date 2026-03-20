import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Localization from 'expo-localization';

import en from '../translations/en.json';
import sw from '../translations/sw.json';
import fr from '../translations/fr.json';
import it from '../translations/it.json';

const LANGUAGE_KEY = 'app_language';

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸', nativeName: 'English' },
  { code: 'sw', name: 'Swahili', flag: '🇹🇿', nativeName: 'Kiswahili' },
  { code: 'fr', name: 'French', flag: '🇫🇷', nativeName: 'Français' },
  { code: 'it', name: 'Italian', flag: '🇮🇹', nativeName: 'Italiano' },
];

export const getStoredLanguage = async (): Promise<string> => {
  try {
    const stored = await AsyncStorage.getItem(LANGUAGE_KEY);
    if (stored) return stored;
    // Fall back to device locale
    const deviceLocale = Localization.getLocales()[0]?.languageCode ?? 'en';
    const supported = SUPPORTED_LANGUAGES.find((l) => l.code === deviceLocale);
    return supported ? deviceLocale : 'en';
  } catch {
    return 'en';
  }
};

export const saveLanguage = async (code: string): Promise<void> => {
  await AsyncStorage.setItem(LANGUAGE_KEY, code);
};

export const changeLanguage = async (code: string): Promise<void> => {
  await saveLanguage(code);
  await i18next.changeLanguage(code);
};

const initI18n = async () => {
  const savedLanguage = await getStoredLanguage();

  await i18next.use(initReactI18next).init({
    compatibilityJSON: 'v4',
    resources: {
      en: { translation: en },
      sw: { translation: sw },
      fr: { translation: fr },
      it: { translation: it },
    },
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  });
};

initI18n();

export default i18next;
