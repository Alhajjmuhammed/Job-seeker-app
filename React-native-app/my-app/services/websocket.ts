import { Platform } from 'react-native';
import API_CONFIG from '../config/api';
import * as SecureStorage from './secureStorage';

interface WebSocketMessage {
  type: string;
  data: any;
}

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private connectionStateListeners: ((connected: boolean) => void)[] = [];
  private isManuallyDisconnected = false;

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    try {
      // Don't connect if already connected or manually disconnected
      if (this.ws?.readyState === WebSocket.OPEN || this.isManuallyDisconnected) {
        return;
      }

      // WebSocket is now enabled - Django Channels is configured on the backend
      console.log('[WebSocket] Connecting to WebSocket server...');

      const token = await SecureStorage.getToken();
      if (!token) {
        console.log('No auth token, skipping WebSocket connection');
        return;
      }

      // Convert HTTP/HTTPS URL to WS/WSS (use BASE_URL, not API_URL)
      // WebSocket routes are at root level, not under /api/
      const wsUrl = API_CONFIG.BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
      const url = `${wsUrl}/ws/notifications/?token=${token}`;

      if (__DEV__) {
        console.log('Connecting to WebSocket:', wsUrl);
      }

      const ws = new WebSocket(url);
      this.ws = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.isManuallyDisconnected = false;
        this.notifyConnectionStateListeners(true);
        this.startPingInterval();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.notifyConnectionStateListeners(false);
        this.stopPingInterval();

        // Attempt reconnection if not manually disconnected
        if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManuallyDisconnected = true;
    this.stopPingInterval();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.notifyConnectionStateListeners(false);
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5);

    console.log(`Scheduling WebSocket reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay) as any;
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping', {});
      }
    }, 30000) as any; // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Send message to server
   */
  send(type: string, data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  /**
   * Backend real-time events (new messages, job/application status changes,
   * payments) are broadcast via NotificationService._broadcast_notification
   * (worker_connect/notification_service.py) or messaging.py's
   * send_user_notification, both of which always wrap the payload in a
   * generic top-level `{ type: 'notification', data: {...} }` envelope -
   * there is no separate top-level 'job_update' / 'application_status' /
   * 'message_received' message ever sent. The inner event is identified by
   * `data.notification_type` (for Notification-model-backed events) or
   * `data.type` (for the ad-hoc message-received push in messaging.py).
   * Map those inner identifiers to the specific event names this service
   * exposes via `on()` so subscribeToJobUpdates/ApplicationUpdates/
   * MessageNotifications actually fire instead of silently never running.
   */
  private static readonly NOTIFICATION_TYPE_TO_EVENT: Record<string, string> = {
    new_message: 'message_received',
    message_received: 'message_received',
    job_assigned: 'job_update',
    job_accepted: 'job_update',
    job_rejected: 'job_update',
    job_completed: 'job_update',
    job_application: 'application_status',
    payment_received: 'payment_update',
  };

  /**
   * Handle incoming message
   */
  private handleMessage(message: WebSocketMessage): void {
    console.log('WebSocket message received:', message.type);

    this.dispatch(message.type, message.data);

    if (message.type === 'notification' && message.data) {
      const innerType = message.data.notification_type || message.data.type;
      const mappedEvent = WebSocketService.NOTIFICATION_TYPE_TO_EVENT[innerType];
      if (mappedEvent) {
        this.dispatch(mappedEvent, message.data);
      }
    }

    // Also notify wildcard listeners
    const wildcardHandlers = this.messageHandlers.get('*') || [];
    wildcardHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in wildcard handler:', error);
      }
    });
  }

  /**
   * Invoke all handlers registered for a given message type.
   */
  private dispatch(type: string, data: any): void {
    const handlers = this.messageHandlers.get(type) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  /**
   * Subscribe to specific message type
   */
  on(messageType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    
    this.messageHandlers.get(messageType)!.push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(messageType);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Subscribe to connection state changes
   */
  onConnectionStateChange(listener: (connected: boolean) => void): () => void {
    this.connectionStateListeners.push(listener);

    // Immediately notify of current state
    listener(this.isConnected());

    // Return unsubscribe function
    return () => {
      const index = this.connectionStateListeners.indexOf(listener);
      if (index > -1) {
        this.connectionStateListeners.splice(index, 1);
      }
    };
  }

  /**
   * Notify all connection state listeners
   */
  private notifyConnectionStateListeners(connected: boolean): void {
    this.connectionStateListeners.forEach(listener => {
      try {
        listener(connected);
      } catch (error) {
        console.error('Error in connection state listener:', error);
      }
    });
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection state
   */
  getConnectionState(): 'connecting' | 'connected' | 'disconnected' {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      default:
        return 'disconnected';
    }
  }
}

export default new WebSocketService();
