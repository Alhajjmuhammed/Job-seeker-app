import { Platform } from 'react-native';
import apiService from './api';

// Note: expo-notifications is not available in Expo Go SDK 53+
// All notification functionality will be silently skipped in that environment
// This is expected behavior - for full notification support, use a development build

console.log('[Push Notifications] Service loaded - notifications disabled in Expo Go SDK 53+');

export interface PushNotificationToken {
  token: string;
  type: 'expo' | 'fcm' | 'apns';
}

class PushNotificationService {
  private notificationListener: any = null;
  private responseListener: any = null;

  /**
   * Register for push notifications and get the token
   */
  async registerForPushNotifications(): Promise<string | null> {
    // Push notifications are not available in Expo Go SDK 53+
    console.log('[Push Notifications] Not available in Expo Go SDK 53+ - use development build');
    return null;
  }

  /**
   * Send push token to backend
   */
  private async sendTokenToBackend(token: string): Promise<void> {
    try {
      await apiService.registerPushToken(token, Platform.OS);
      console.log('Push token registered with backend');
    } catch (error) {
      console.error('Error sending token to backend:', error);
    }
  }

  /**
   * Set up notification listeners
   */
  setupNotificationListeners(
    onNotificationReceived?: (notification: any) => void,
    onNotificationTapped?: (response: any) => void
  ): void {
    // Not available in Expo Go SDK 53+
    console.log('[Push Notifications] Listeners not available in Expo Go');
    return;
  }

  /**
   * Remove notification listeners
   */
  removeNotificationListeners(): void {
    // Not available in Expo Go
    return;
  }

  /**
   * Get badge count
   */
  async getBadgeCount(): Promise<number> {
    return 0;
  }

  /**
   * Set badge count
   */
  async setBadgeCount(count: number): Promise<void> {
    // Not available in Expo Go
    return;
  }

  /**
   * Clear all notifications
   */
  async clearAllNotifications(): Promise<void> {
    // Not available in Expo Go
    return;
  }

  /**
   * Schedule a local notification
   */
  async scheduleLocalNotification(
    title: string,
    body: string,
    data?: any,
    delay: number = 0
  ): Promise<string> {
    // Not available in Expo Go
    return '';
  }

  /**
   * Cancel a scheduled notification
   */
  async cancelScheduledNotification(notificationId: string): Promise<void> {
    // Not available in Expo Go
    return;
  }

  /**
   * Check if notifications are enabled
   */
  async areNotificationsEnabled(): Promise<boolean> {
    return false;
  }

  /**
   * Open system notification settings
   */
  async openNotificationSettings(): Promise<void> {
    // Not available in Expo Go
    return;
  }
}

export default new PushNotificationService();
