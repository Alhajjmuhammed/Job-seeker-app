import { Platform } from 'react-native';
import Constants, { ExecutionEnvironment } from 'expo-constants';
import * as Device from 'expo-device';
import apiService from './api';

// Remote push notifications require a development/production build - Expo
// Go (SDK 53+) dropped remote push support, so every call below detects
// that environment at runtime and no-ops instead of crashing. In a real
// dev/production build (which is what any actual release uses), this
// registers and delivers real push notifications via expo-notifications.
const isExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;

// expo-notifications must not be imported/used in Expo Go on SDK 53+, so
// it's loaded lazily and only when we're actually going to use it.
let Notifications: typeof import('expo-notifications') | null = null;
function getNotificationsModule() {
  if (isExpoGo) return null;
  if (!Notifications) {
    Notifications = require('expo-notifications');
    Notifications!.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
        shouldShowBanner: true,
        shouldShowList: true,
      }),
    });
  }
  return Notifications;
}

export interface PushNotificationToken {
  token: string;
  type: 'expo' | 'fcm' | 'apns';
}

class PushNotificationService {
  private notificationListener: any = null;
  private responseListener: any = null;

  /**
   * Register for push notifications and get the token. Returns null (and
   * logs why) in Expo Go, on a simulator, or if permission is denied.
   */
  async registerForPushNotifications(): Promise<string | null> {
    if (isExpoGo) {
      console.log('[Push Notifications] Not available in Expo Go SDK 53+ - use a development build');
      return null;
    }

    const notif = getNotificationsModule();
    if (!notif) return null;

    try {
      if (!Device.isDevice) {
        console.log('[Push Notifications] Push tokens require a physical device');
        return null;
      }

      const { status: existingStatus } = await notif.getPermissionsAsync();
      let finalStatus = existingStatus;
      if (existingStatus !== 'granted') {
        const { status } = await notif.requestPermissionsAsync();
        finalStatus = status;
      }
      if (finalStatus !== 'granted') {
        console.log('[Push Notifications] Permission not granted');
        return null;
      }

      if (Platform.OS === 'android') {
        await notif.setNotificationChannelAsync('default', {
          name: 'default',
          importance: notif.AndroidImportance.MAX,
        });
      }

      const projectId =
        Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
      if (!projectId) {
        console.error('[Push Notifications] No EAS projectId configured in app.json');
        return null;
      }

      const tokenData = await notif.getExpoPushTokenAsync({ projectId });
      await this.sendTokenToBackend(tokenData.data);
      return tokenData.data;
    } catch (error) {
      console.error('[Push Notifications] Error registering for push notifications:', error);
      return null;
    }
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
    const notif = getNotificationsModule();
    if (!notif) {
      console.log('[Push Notifications] Listeners not available in Expo Go');
      return;
    }

    if (onNotificationReceived) {
      this.notificationListener = notif.addNotificationReceivedListener(onNotificationReceived);
    }
    if (onNotificationTapped) {
      this.responseListener = notif.addNotificationResponseReceivedListener(onNotificationTapped);
    }
  }

  /**
   * Remove notification listeners
   */
  removeNotificationListeners(): void {
    if (this.notificationListener) {
      this.notificationListener.remove();
      this.notificationListener = null;
    }
    if (this.responseListener) {
      this.responseListener.remove();
      this.responseListener = null;
    }
  }

  /**
   * Get badge count
   */
  async getBadgeCount(): Promise<number> {
    const notif = getNotificationsModule();
    if (!notif) return 0;
    try {
      return await notif.getBadgeCountAsync();
    } catch {
      return 0;
    }
  }

  /**
   * Set badge count
   */
  async setBadgeCount(count: number): Promise<void> {
    const notif = getNotificationsModule();
    if (!notif) return;
    try {
      await notif.setBadgeCountAsync(count);
    } catch (error) {
      console.error('Error setting badge count:', error);
    }
  }

  /**
   * Clear all notifications
   */
  async clearAllNotifications(): Promise<void> {
    const notif = getNotificationsModule();
    if (!notif) return;
    try {
      await notif.dismissAllNotificationsAsync();
    } catch (error) {
      console.error('Error clearing notifications:', error);
    }
  }

  /**
   * Schedule a local notification (works in Expo Go too, unlike remote push)
   */
  async scheduleLocalNotification(
    title: string,
    body: string,
    data?: any,
    delay: number = 0
  ): Promise<string> {
    const notif = getNotificationsModule();
    if (!notif) return '';
    try {
      return await notif.scheduleNotificationAsync({
        content: { title, body, data },
        trigger:
          delay > 0
            ? { type: notif.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds: delay }
            : null,
      });
    } catch (error) {
      console.error('Error scheduling local notification:', error);
      return '';
    }
  }

  /**
   * Cancel a scheduled notification
   */
  async cancelScheduledNotification(notificationId: string): Promise<void> {
    const notif = getNotificationsModule();
    if (!notif || !notificationId) return;
    try {
      await notif.cancelScheduledNotificationAsync(notificationId);
    } catch (error) {
      console.error('Error cancelling scheduled notification:', error);
    }
  }

  /**
   * Check if notifications are enabled
   */
  async areNotificationsEnabled(): Promise<boolean> {
    const notif = getNotificationsModule();
    if (!notif) return false;
    try {
      const { status } = await notif.getPermissionsAsync();
      return status === 'granted';
    } catch {
      return false;
    }
  }

  /**
   * Open system notification settings
   */
  async openNotificationSettings(): Promise<void> {
    if (isExpoGo) return;
    try {
      const { Linking } = require('react-native');
      await Linking.openSettings();
    } catch (error) {
      console.error('Error opening notification settings:', error);
    }
  }
}

export default new PushNotificationService();
