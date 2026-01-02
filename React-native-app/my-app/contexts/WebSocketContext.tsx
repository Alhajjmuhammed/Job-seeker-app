import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import websocketService from '../services/websocket';
import { useAuth } from './AuthContext';
import { useNotifications } from './NotificationContext';

interface WebSocketContextType {
  connected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  subscribeToJobUpdates: (handler: (data: any) => void) => () => void;
  subscribeToApplicationUpdates: (handler: (data: any) => void) => () => void;
  subscribeToMessageNotifications: (handler: (data: any) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { refreshUnreadCount } = useNotifications();
  const [connected, setConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    // Only connect if user is logged in
    if (!user) {
      return;
    }

    // Connect to WebSocket
    websocketService.connect();

    // Subscribe to connection state changes
    const unsubscribe = websocketService.onConnectionStateChange((isConnected) => {
      setConnected(isConnected);
      setConnectionState(websocketService.getConnectionState());
    });

    // Set up global message handlers
    setupGlobalHandlers();

    // Handle app state changes (background/foreground)
    const subscription = AppState.addEventListener('change', handleAppStateChange);

    return () => {
      unsubscribe();
      subscription.remove();
      websocketService.disconnect();
    };
  }, [user]);

  const handleAppStateChange = (nextAppState: AppStateStatus) => {
    if (nextAppState === 'active') {
      // App came to foreground, reconnect if needed
      if (!websocketService.isConnected() && user) {
        websocketService.connect();
      }
    } else if (nextAppState === 'background') {
      // App went to background, keep connection alive for notifications
      // iOS will maintain the connection for a while
    }
  };

  const setupGlobalHandlers = () => {
    // Handle notification events
    websocketService.on('notification', (data) => {
      console.log('New notification via WebSocket:', data);
      refreshUnreadCount();
    });

    // Handle job updates
    websocketService.on('job_update', (data) => {
      console.log('Job update via WebSocket:', data);
    });

    // Handle application status updates
    websocketService.on('application_status', (data) => {
      console.log('Application status update via WebSocket:', data);
      refreshUnreadCount();
    });

    // Handle new messages
    websocketService.on('message_received', (data) => {
      console.log('New message via WebSocket:', data);
      refreshUnreadCount();
    });

    // Handle payment updates
    websocketService.on('payment_update', (data) => {
      console.log('Payment update via WebSocket:', data);
    });

    // Handle broadcast messages
    websocketService.on('broadcast_message', (data) => {
      console.log('Broadcast message via WebSocket:', data);
    });
  };

  const subscribeToJobUpdates = (handler: (data: any) => void) => {
    return websocketService.on('job_update', handler);
  };

  const subscribeToApplicationUpdates = (handler: (data: any) => void) => {
    return websocketService.on('application_status', handler);
  };

  const subscribeToMessageNotifications = (handler: (data: any) => void) => {
    return websocketService.on('message_received', handler);
  };

  return (
    <WebSocketContext.Provider
      value={{
        connected,
        connectionState,
        subscribeToJobUpdates,
        subscribeToApplicationUpdates,
        subscribeToMessageNotifications,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}
