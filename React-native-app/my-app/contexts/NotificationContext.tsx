import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'expo-router';
import pushNotificationService from '../services/pushNotifications';
import apiService from '../services/api';
import { getToken } from '../services/secureStorage';

interface NotificationContextType {
  unreadCount: number;
  refreshUnreadCount: () => Promise<void>;
  handleNotificationTap: (response: any) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    // Register for push notifications
    registerPushNotifications();

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
    } catch (error) {
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
    // Increment unread count
    setUnreadCount(prev => prev + 1);
    
    // Update badge
    pushNotificationService.setBadgeCount(unreadCount + 1);
  };

  const handleNotificationTap = (response: any) => {
    const data = response.notification.request.content.data;
    
    // Navigate based on notification type
    if (data.type === 'job_posted' || data.type === 'job_update') {
      if (data.job_id) {
        router.push(`/job/${data.job_id}` as any);
      } else {
        router.push('/(worker)/browse-jobs' as any);
      }
    } else if (data.type === 'application_accepted' || data.type === 'application_rejected') {
      router.push('/(worker)/jobs' as any);
    } else if (data.type === 'new_message') {
      if (data.user_id) {
        router.push(`/(worker)/messages/${data.user_id}` as any);
      } else {
        router.push('/(worker)/messages' as any);
      }
    } else if (data.type === 'direct_hire_request') {
      router.push('/(worker)/dashboard' as any);
    } else if (data.type === 'service_request_assigned' || data.type === 'assignment_received') {
      // Worker received new assignment
      if (data.assignment_id) {
        router.push(`/(worker)/assignments/respond/${data.assignment_id}` as any);
      } else {
        router.push('/(worker)/assignments/pending' as any);
      }
    } else if (data.type === 'assignment_accepted' || data.type === 'worker_accepted') {
      // Client - worker accepted assignment
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      } else {
        router.push('/(client)/my-requests' as any);
      }
    } else if (data.type === 'assignment_rejected' || data.type === 'worker_rejected') {
      // Client - worker rejected assignment
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      } else {
        router.push('/(client)/my-requests' as any);
      }
    } else if (data.type === 'worker_clocked_in' || data.type === 'worker_clocked_out') {
      // Client - worker clocked in/out
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      } else {
        router.push('/(client)/my-requests' as any);
      }
    } else if (data.type === 'service_completed') {
      // Client - service marked complete
      if (data.request_id) {
        router.push(`/(client)/service-request/${data.request_id}` as any);
      } else {
        router.push('/(client)/my-requests' as any);
      }
    } else if (data.type === 'service_request_created') {
      // Client created service request (admin notification)
      router.push('/(client)/my-requests' as any);
    } else {
      // Default: go to notifications screen
      router.push('/(worker)/notifications' as any);
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
