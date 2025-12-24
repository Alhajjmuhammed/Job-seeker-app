import { TextStyle } from 'react-native';

interface ThemeFonts {
  fontRegular: string;
  fontMedium: string;
  fontSemiBold: string;
  fontBold: string;
}

export const applyFontFamily = (style: TextStyle, theme: ThemeFonts): TextStyle => {
  if (!style.fontWeight || style.fontWeight === 'normal' || style.fontWeight === '400') {
    return { ...style, fontFamily: theme.fontRegular };
  } else if (style.fontWeight === '500') {
    return { ...style, fontFamily: theme.fontMedium };
  } else if (style.fontWeight === '600' || style.fontWeight === 'semi-bold') {
    return { ...style, fontFamily: theme.fontSemiBold };
  } else if (style.fontWeight === 'bold' || style.fontWeight === '700') {
    return { ...style, fontFamily: theme.fontBold };
  }
  return { ...style, fontFamily: theme.fontRegular };
};

export const text = {
  h1: (theme: ThemeFonts) => ({
    fontFamily: theme.fontBold,
    fontWeight: 'bold' as const,
  }),
  h2: (theme: ThemeFonts) => ({
    fontFamily: theme.fontBold,
    fontWeight: 'bold' as const,
  }),
  h3: (theme: ThemeFonts) => ({
    fontFamily: theme.fontSemiBold,
    fontWeight: '600' as const,
  }),
  body: (theme: ThemeFonts) => ({
    fontFamily: theme.fontRegular,
    fontWeight: 'normal' as const,
  }),
  bodyMedium: (theme: ThemeFonts) => ({
    fontFamily: theme.fontMedium,
    fontWeight: '500' as const,
  }),
  bodySemiBold: (theme: ThemeFonts) => ({
    fontFamily: theme.fontSemiBold,
    fontWeight: '600' as const,
  }),
  caption: (theme: ThemeFonts) => ({
    fontFamily: theme.fontRegular,
    fontWeight: 'normal' as const,
  }),
};
