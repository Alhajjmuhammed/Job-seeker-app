import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { useRouter } from 'expo-router';
import pushNotificationService from '../services/pushNotifications';
import apiService from '../services/api';
import { getToken } from '../services/secureStorage';
import { useAuth } from './AuthContext';
import { routeForNotification } from '../utils/notificationRoute';

interface NotificationContextType {
  unreadCount: number;
  refreshUnreadCount: () => Promise<void>;
  handleNotificationTap: (response: any) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState(0);
  const { user } = useAuth();
  // The tap listener is registered once on mount, so it would keep the role
  // from that moment (usually logged out). Read the current role from a ref.
  const roleRef = useRef<string | undefined>(user?.userType);
  roleRef.current = user?.userType;

  // Registering needs a logged-in user. This ran once at start-up, so on a
  // fresh install (logged out) the server answered 401 and the user got no
  // push notifications until the app was restarted after logging in.
  useEffect(() => {
    if (user?.id) {
      registerPushNotifications();
      refreshUnreadCount();
    } else {
      setUnreadCount(0);
    }
  }, [user?.id]);

  useEffect(() => {
    // Set up notification listeners
    pushNotificationService.setupNotificationListeners(
      handleNotificationReceived,
      handleNotificationTap
    );

    // Load initial unread count
    refreshUnreadCount();

    // Clean up listeners on unmount
    return () => {
      pushNotificationService.removeNotificationListeners();
    };
  }, []);

  const registerPushNotifications = async () => {
    try {
      await pushNotificationService.registerForPushNotifications();
    } catch (error) {
      console.error('Error registering push notifications:', error);
    }
  };

  const refreshUnreadCount = async () => {
    try {
      // Only fetch if user is authenticated
      const token = await getToken();
      if (!token) {
        setUnreadCount(0);
        return;
      }
      
      const response = await apiService.getUnreadNotificationCount();
      setUnreadCount(response.count || 0);
      
      // Update badge count
      await pushNotificationService.setBadgeCount(response.count || 0);
    } catch (error: any) {
      // If authentication fails, reset count to 0
      if (error.response?.status === 401) {
        setUnreadCount(0);
        await pushNotificationService.setBadgeCount(0);
      } else {
        console.error('Error fetching unread count:', error);
      }
    }
  };

  const handleNotificationReceived = (notification: any) => {
    // This listener is registered once in the mount-only effect above, so
    // it permanently closes over unreadCount's value at that time (0) -
    // reading `unreadCount` directly here set the OS badge to 1 on every
    // notification after the first, regardless of how many had actually
    // arrived. Set it from inside the functional updater instead, which
    // always sees the true current count.
    setUnreadCount(prev => {
      const next = prev + 1;
      pushNotificationService.setBadgeCount(next);
      return next;
    });
  };

  const handleNotificationTap = (response: any) => {
    const data = response?.notification?.request?.content?.data || {};
    const role = roleRef.current;

    // Same routing as the notification lists. A push may carry the stored
    // notification's fields (notification_type + extra_data) or a flat
    // payload with `type` and the ids at the top level - accept both.
    try {
      const href = routeForNotification({
        type: data.notification_type ?? data.type,
        data: data.extra_data ?? data,
        role,
      });
      if (href) {
        router.push(href as any);
      } else if (role === 'worker' || role === 'client') {
        router.push(`/(${role})/notifications` as any);
      }
    } catch (error) {
      console.error('Error opening notification:', error);
    }

    // Mark as read
    if (data.notification_id) {
      apiService.markNotificationAsRead(data.notification_id).catch(console.error);
    }

    // Refresh unread count
    refreshUnreadCount();
  };

  return (
    <NotificationContext.Provider value={{ unreadCount, refreshUnreadCount, handleNotificationTap }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}
