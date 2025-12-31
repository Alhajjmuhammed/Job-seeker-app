/**
 * Push Notification Service for Worker Connect Mobile App
 * 
 * Handles registration, permissions, and notification management.
 */

import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

// Storage keys
const STORAGE_KEYS = {
  PUSH_TOKEN: '@workerconnect_push_token',
  NOTIFICATION_SETTINGS: '@workerconnect_notification_settings',
};

// Notification categories/types
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
  reviews: boolean;
  payments: boolean;
  marketing: boolean;
  sound: boolean;
  vibration: boolean;
  badge: boolean;
}

// Default notification settings
export const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  enabled: true,
  jobs: true,
  applications: true,
  messages: true,
  reviews: true,
  payments: true,
  marketing: false,
  sound: true,
  vibration: true,
  badge: true,
};

class PushNotificationService {
  private expoPushToken: string | null = null;
  private settings: NotificationSettings = DEFAULT_NOTIFICATION_SETTINGS;
  private notificationListener: Notifications.Subscription | null = null;
  private responseListener: Notifications.Subscription | null = null;

  /**
   * Initialize the push notification service
   */
  async initialize(): Promise<void> {
    // Load saved settings
    await this.loadSettings();

    // Configure notification handler
    Notifications.setNotificationHandler({
      handleNotification: async (notification) => {
        const data = notification.request.content.data;
        const type = data?.type as NotificationType;

        // Check if this notification type is enabled
        const shouldShow = this.shouldShowNotification(type);

        return {
          shouldShowAlert: shouldShow,
          shouldPlaySound: shouldShow && this.settings.sound,
          shouldSetBadge: shouldShow && this.settings.badge,
        };
      },
    });

    // Set up notification categories (for actionable notifications)
    await this.setupNotificationCategories();
  }

  /**
   * Register for push notifications
   */
  async registerForPushNotifications(): Promise<string | null> {
    // Check if running on physical device
    if (!Device.isDevice) {
      console.log('Push notifications require a physical device');
      return null;
    }

    // Check/request permissions
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('Push notification permission denied');
      return null;
    }

    try {
      // Get Expo push token
      const projectId = Constants.expoConfig?.extra?.eas?.projectId;
      const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId,
      });

      this.expoPushToken = tokenData.data;

      // Save token locally
      await AsyncStorage.setItem(STORAGE_KEYS.PUSH_TOKEN, this.expoPushToken);

      // Configure Android channel
      if (Platform.OS === 'android') {
        await this.setupAndroidChannels();
      }

      return this.expoPushToken;
    } catch (error) {
      console.error('Error getting push token:', error);
      return null;
    }
  }

  /**
   * Set up Android notification channels
   */
  private async setupAndroidChannels(): Promise<void> {
    if (Platform.OS !== 'android') return;

    // Main channel
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#4F46E5',
    });

    // Jobs channel
    await Notifications.setNotificationChannelAsync('jobs', {
      name: 'Jobs',
      description: 'Job postings and assignments',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
    });

    // Messages channel
    await Notifications.setNotificationChannelAsync('messages', {
      name: 'Messages',
      description: 'Chat messages',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'message.wav',
    });

    // Applications channel
    await Notifications.setNotificationChannelAsync('applications', {
      name: 'Applications',
      description: 'Job application updates',
      importance: Notifications.AndroidImportance.DEFAULT,
    });

    // Payments channel
    await Notifications.setNotificationChannelAsync('payments', {
      name: 'Payments',
      description: 'Payment and invoice updates',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }

  /**
   * Set up notification categories for actionable notifications
   */
  private async setupNotificationCategories(): Promise<void> {
    await Notifications.setNotificationCategoryAsync('application', [
      {
        identifier: 'accept',
        buttonTitle: 'Accept',
        options: { opensAppToForeground: true },
      },
      {
        identifier: 'reject',
        buttonTitle: 'Reject',
        options: { isDestructive: true },
      },
    ]);

    await Notifications.setNotificationCategoryAsync('message', [
      {
        identifier: 'reply',
        buttonTitle: 'Reply',
        textInput: {
          submitButtonTitle: 'Send',
          placeholder: 'Type a message...',
        },
      },
      {
        identifier: 'mark_read',
        buttonTitle: 'Mark as Read',
      },
    ]);

    await Notifications.setNotificationCategoryAsync('job', [
      {
        identifier: 'view',
        buttonTitle: 'View Job',
        options: { opensAppToForeground: true },
      },
      {
        identifier: 'apply',
        buttonTitle: 'Apply Now',
        options: { opensAppToForeground: true },
      },
    ]);
  }

  /**
   * Check if a notification type should be shown
   */
  private shouldShowNotification(type: NotificationType): boolean {
    if (!this.settings.enabled) return false;

    switch (type) {
      case NotificationType.JOB_POSTED:
      case NotificationType.JOB_ASSIGNED:
      case NotificationType.JOB_COMPLETED:
      case NotificationType.JOB_CANCELLED:
        return this.settings.jobs;

      case NotificationType.APPLICATION_RECEIVED:
      case NotificationType.APPLICATION_ACCEPTED:
      case NotificationType.APPLICATION_REJECTED:
        return this.settings.applications;

      case NotificationType.NEW_MESSAGE:
        return this.settings.messages;

      case NotificationType.NEW_REVIEW:
        return this.settings.reviews;

      case NotificationType.INVOICE_SENT:
      case NotificationType.INVOICE_RECEIVED:
      case NotificationType.PAYMENT_RECEIVED:
      case NotificationType.PAYMENT_REMINDER:
        return this.settings.payments;

      case NotificationType.SYSTEM_ANNOUNCEMENT:
        return this.settings.marketing;

      default:
        return true;
    }
  }

  /**
   * Get the Android channel for a notification type
   */
  getChannelForType(type: NotificationType): string {
    switch (type) {
      case NotificationType.JOB_POSTED:
      case NotificationType.JOB_ASSIGNED:
      case NotificationType.JOB_COMPLETED:
      case NotificationType.JOB_CANCELLED:
        return 'jobs';

      case NotificationType.NEW_MESSAGE:
        return 'messages';

      case NotificationType.APPLICATION_RECEIVED:
      case NotificationType.APPLICATION_ACCEPTED:
      case NotificationType.APPLICATION_REJECTED:
        return 'applications';

      case NotificationType.INVOICE_SENT:
      case NotificationType.INVOICE_RECEIVED:
      case NotificationType.PAYMENT_RECEIVED:
      case NotificationType.PAYMENT_REMINDER:
        return 'payments';

      default:
        return 'default';
    }
  }

  /**
   * Load notification settings from storage
   */
  async loadSettings(): Promise<NotificationSettings> {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEYS.NOTIFICATION_SETTINGS);
      if (stored) {
        this.settings = { ...DEFAULT_NOTIFICATION_SETTINGS, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.error('Error loading notification settings:', error);
    }
    return this.settings;
  }

  /**
   * Save notification settings
   */
  async saveSettings(settings: Partial<NotificationSettings>): Promise<void> {
    this.settings = { ...this.settings, ...settings };
    await AsyncStorage.setItem(
      STORAGE_KEYS.NOTIFICATION_SETTINGS,
      JSON.stringify(this.settings)
    );
  }

  /**
   * Get current notification settings
   */
  getSettings(): NotificationSettings {
    return { ...this.settings };
  }

  /**
   * Get stored push token
   */
  async getPushToken(): Promise<string | null> {
    if (this.expoPushToken) return this.expoPushToken;
    
    try {
      this.expoPushToken = await AsyncStorage.getItem(STORAGE_KEYS.PUSH_TOKEN);
      return this.expoPushToken;
    } catch (error) {
      console.error('Error getting push token from storage:', error);
      return null;
    }
  }

  /**
   * Schedule a local notification
   */
  async scheduleLocalNotification(
    title: string,
    body: string,
    data?: Record<string, unknown>,
    trigger?: Notifications.NotificationTriggerInput
  ): Promise<string> {
    return await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data,
        sound: this.settings.sound ? 'default' : undefined,
      },
      trigger: trigger || null,
    });
  }

  /**
   * Cancel a scheduled notification
   */
  async cancelNotification(notificationId: string): Promise<void> {
    await Notifications.cancelScheduledNotificationAsync(notificationId);
  }

  /**
   * Cancel all scheduled notifications
   */
  async cancelAllNotifications(): Promise<void> {
    await Notifications.cancelAllScheduledNotificationsAsync();
  }

  /**
   * Get all scheduled notifications
   */
  async getScheduledNotifications(): Promise<Notifications.NotificationRequest[]> {
    return await Notifications.getAllScheduledNotificationsAsync();
  }

  /**
   * Get badge count
   */
  async getBadgeCount(): Promise<number> {
    return await Notifications.getBadgeCountAsync();
  }

  /**
   * Set badge count
   */
  async setBadgeCount(count: number): Promise<void> {
    await Notifications.setBadgeCountAsync(count);
  }

  /**
   * Clear badge
   */
  async clearBadge(): Promise<void> {
    await Notifications.setBadgeCountAsync(0);
  }

  /**
   * Add notification received listener
   */
  addNotificationListener(
    callback: (notification: Notifications.Notification) => void
  ): Notifications.Subscription {
    return Notifications.addNotificationReceivedListener(callback);
  }

  /**
   * Add notification response listener
   */
  addResponseListener(
    callback: (response: Notifications.NotificationResponse) => void
  ): Notifications.Subscription {
    return Notifications.addNotificationResponseReceivedListener(callback);
  }

  /**
   * Clean up listeners
   */
  cleanup(): void {
    if (this.notificationListener) {
      this.notificationListener.remove();
      this.notificationListener = null;
    }
    if (this.responseListener) {
      this.responseListener.remove();
      this.responseListener = null;
    }
  }
}

// Export singleton instance
export const pushNotificationService = new PushNotificationService();

// Export hook for React components
export function usePushNotifications() {
  return {
    registerForPushNotifications: () => pushNotificationService.registerForPushNotifications(),
    getPushToken: () => pushNotificationService.getPushToken(),
    getSettings: () => pushNotificationService.getSettings(),
    saveSettings: (settings: Partial<NotificationSettings>) => pushNotificationService.saveSettings(settings),
    scheduleLocalNotification: pushNotificationService.scheduleLocalNotification.bind(pushNotificationService),
    cancelNotification: pushNotificationService.cancelNotification.bind(pushNotificationService),
    getBadgeCount: () => pushNotificationService.getBadgeCount(),
    setBadgeCount: (count: number) => pushNotificationService.setBadgeCount(count),
    clearBadge: () => pushNotificationService.clearBadge(),
    addNotificationListener: pushNotificationService.addNotificationListener.bind(pushNotificationService),
    addResponseListener: pushNotificationService.addResponseListener.bind(pushNotificationService),
  };
}

export default pushNotificationService;
