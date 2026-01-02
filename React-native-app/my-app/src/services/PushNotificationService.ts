import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Push notifications are not available in Expo Go SDK 53+
// This service provides stub implementations that do nothing
console.log('[PushNotificationService] Notifications disabled in Expo Go SDK 53+');

// Storage keys
const STORAGE_KEYS = {
  PUSH_TOKEN: '@workerconnect_push_token',
  NOTIFICATION_SETTINGS: '@workerconnect_notification_settings',
};

// Notification types
export enum NotificationType {
  JOB_POSTED = 'job_posted',
  JOB_ASSIGNED = 'job_assigned',
  JOB_COMPLETED = 'job_completed',
  JOB_CANCELLED = 'job_cancelled',
  APPLICATION_RECEIVED = 'application_received',
  APPLICATION_ACCEPTED = 'application_accepted',
  APPLICATION_REJECTED = 'application_rejected',
  NEW_MESSAGE = 'new_message',
  NEW_REVIEW = 'new_review',
  INVOICE_SENT = 'invoice_sent',
  INVOICE_RECEIVED = 'invoice_received',
  PAYMENT_RECEIVED = 'payment_received',
  PAYMENT_REMINDER = 'payment_reminder',
  BADGE_EARNED = 'badge_earned',
  VERIFICATION_APPROVED = 'verification_approved',
  SYSTEM_ANNOUNCEMENT = 'system_announcement',
}

// Notification settings interface
export interface NotificationSettings {
  enabled: boolean;
  jobs: boolean;
  applications: boolean;
  messages: boolean;
  payments: boolean;
  reviews: boolean;
  system: boolean;
  sound: boolean;
  vibration: boolean;
  badge: boolean;
}

// Default notification settings
const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  enabled: true,
  jobs: true,
  applications: true,
  messages: true,
  payments: true,
  reviews: true,
  system: true,
  sound: true,
  vibration: true,
  badge: true,
};

class PushNotificationService {
  private expoPushToken: string | null = null;
  private settings: NotificationSettings = DEFAULT_NOTIFICATION_SETTINGS;
  private notificationListener: any = null;
  private responseListener: any = null;

  async initialize(): Promise<void> {
    console.log('[PushNotificationService] Skipping initialization - not available in Expo Go');
    await this.loadSettings();
  }

  async registerForPushNotifications(): Promise<string | null> {
    console.log('[PushNotificationService] Not available in Expo Go');
    return null;
  }

  async loadSettings(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEYS.NOTIFICATION_SETTINGS);
      if (stored) {
        this.settings = JSON.parse(stored);
      }
    } catch (error) {
      console.log('[PushNotificationService] Error loading settings:', error);
    }
  }

  async saveSettings(settings: Partial<NotificationSettings>): Promise<void> {
    this.settings = { ...this.settings, ...settings };
    await AsyncStorage.setItem(
      STORAGE_KEYS.NOTIFICATION_SETTINGS,
      JSON.stringify(this.settings)
    );
  }

  getSettings(): NotificationSettings {
    return this.settings;
  }

  async getPushToken(): Promise<string | null> {
    return null;
  }

  async scheduleLocalNotification(
    title: string,
    body: string,
    data?: Record<string, unknown>,
    trigger?: any
  ): Promise<string> {
    return '';
  }

  async cancelScheduledNotification(notificationId: string): Promise<void> {
    return;
  }

  async cancelAllNotifications(): Promise<void> {
    return;
  }

  async getScheduledNotifications(): Promise<any[]> {
    return [];
  }

  async getBadgeCount(): Promise<number> {
    return 0;
  }

  async setBadgeCount(count: number): Promise<void> {
    return;
  }

  async clearBadge(): Promise<void> {
    return;
  }

  addNotificationListener(callback: (notification: any) => void): any {
    return { remove: () => {} };
  }

  addResponseListener(callback: (response: any) => void): any {
    return { remove: () => {} };
  }

  cleanup(): void {
    return;
  }
}

export const pushNotificationService = new PushNotificationService();
export default pushNotificationService;

// Helper hook for React components
export function usePushNotifications() {
  return {
    initialize: () => pushNotificationService.initialize(),
    register: () => pushNotificationService.registerForPushNotifications(),
    getSettings: () => pushNotificationService.getSettings(),
    saveSettings: (settings: Partial<NotificationSettings>) =>
      pushNotificationService.saveSettings(settings),
    scheduleNotification: (title: string, body: string, data?: any, trigger?: any) =>
      pushNotificationService.scheduleLocalNotification(title, body, data, trigger),
    cancelNotification: (id: string) => pushNotificationService.cancelScheduledNotification(id),
    getBadgeCount: () => pushNotificationService.getBadgeCount(),
    setBadgeCount: (count: number) => pushNotificationService.setBadgeCount(count),
  };
}
