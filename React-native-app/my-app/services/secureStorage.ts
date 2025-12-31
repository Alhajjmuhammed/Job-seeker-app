/**
 * Secure Storage Service
 * Uses expo-secure-store for sensitive data (tokens) and AsyncStorage for non-sensitive data
 */
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// Keys
const TOKEN_KEY = 'auth_token';
const USER_KEY = '@user_data';

/**
 * Check if SecureStore is available (not available on web)
 */
const isSecureStoreAvailable = Platform.OS !== 'web';

/**
 * Securely store the authentication token
 * Uses SecureStore on native platforms, AsyncStorage on web (with warning)
 */
export async function setToken(token: string): Promise<void> {
  try {
    if (isSecureStoreAvailable) {
      await SecureStore.setItemAsync(TOKEN_KEY, token);
    } else {
      // Fallback to AsyncStorage on web (less secure)
      console.warn('SecureStore not available, using AsyncStorage for token');
      await AsyncStorage.setItem(`@${TOKEN_KEY}`, token);
    }
  } catch (error) {
    console.error('Error storing token:', error);
    throw error;
  }
}

/**
 * Retrieve the authentication token
 */
export async function getToken(): Promise<string | null> {
  try {
    if (isSecureStoreAvailable) {
      return await SecureStore.getItemAsync(TOKEN_KEY);
    } else {
      return await AsyncStorage.getItem(`@${TOKEN_KEY}`);
    }
  } catch (error) {
    console.error('Error retrieving token:', error);
    return null;
  }
}

/**
 * Remove the authentication token
 */
export async function removeToken(): Promise<void> {
  try {
    if (isSecureStoreAvailable) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    } else {
      await AsyncStorage.removeItem(`@${TOKEN_KEY}`);
    }
  } catch (error) {
    console.error('Error removing token:', error);
  }
}

/**
 * Store user data (non-sensitive)
 * Uses AsyncStorage as user profile data is not sensitive
 */
export async function setUserData(userData: any): Promise<void> {
  try {
    await AsyncStorage.setItem(USER_KEY, JSON.stringify(userData));
  } catch (error) {
    console.error('Error storing user data:', error);
    throw error;
  }
}

/**
 * Retrieve user data
 */
export async function getUserData(): Promise<any | null> {
  try {
    const data = await AsyncStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Error retrieving user data:', error);
    return null;
  }
}

/**
 * Remove user data
 */
export async function removeUserData(): Promise<void> {
  try {
    await AsyncStorage.removeItem(USER_KEY);
  } catch (error) {
    console.error('Error removing user data:', error);
  }
}

/**
 * Clear all authentication data (token + user data)
 */
export async function clearAuth(): Promise<void> {
  await Promise.all([removeToken(), removeUserData()]);
}

/**
 * Check if user is authenticated (has valid token)
 */
export async function isAuthenticated(): Promise<boolean> {
  const token = await getToken();
  return token !== null && token.length > 0;
}

export default {
  setToken,
  getToken,
  removeToken,
  setUserData,
  getUserData,
  removeUserData,
  clearAuth,
  isAuthenticated,
};
