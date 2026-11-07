/**
 * A picked file (expo-document-picker / expo-image-picker asset) in the shape
 * FormData needs on this platform.
 *
 * Phones: React Native's FormData takes { uri, type, name }.
 * Browser (web preview): FormData needs a real File - the pickers put it on
 * asset.file. Sending { uri, type, name } there uploads the text
 * "[object Object]" and the server answers "file is required".
 */
import { Platform } from 'react-native';

export function uploadable(asset: any, type: string, name: string): any {
  if (Platform.OS === 'web' && asset?.file) {
    return asset.file;
  }
  return { uri: asset.uri, type, name };
}
