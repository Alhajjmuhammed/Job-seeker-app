/**
 * WebSocket Client for Real-time Features
 * 
 * Provides WebSocket connectivity for:
 * - Real-time notifications
 * - Real-time chat/messaging
 * - Job updates
 * 
 * Usage:
 *   // Notifications
 *   const notificationWS = new NotificationWebSocket(authToken);
 *   notificationWS.onNotification((data) => {
 *     console.log('New notification:', data);
 *   });
 * 
 *   // Chat
 *   const chatWS = new ChatWebSocket(conversationId, authToken);
 *   chatWS.onMessage((data) => {
 *     console.log('New message:', data);
 *   });
 */

/**
 * Base WebSocket class with reconnection logic
 */
class BaseWebSocket {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.pingInterval = null;
        this.handlers = {};
        this.isConnecting = false;
    }

    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this.isConnecting = true;
        console.log(`[WebSocket] Connecting to: ${this.url}`);

        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log(`[WebSocket] Connected to: ${this.url}`);
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                this.isConnecting = false;
                this.startPingPong();
                
                if (this.handlers.onOpen) {
                    this.handlers.onOpen();
                }
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log(`[WebSocket] Received:`, data);
                
                if (data.type === 'pong') {
                    // Pong received, connection is alive
                    return;
                }

                this.handleMessage(data);
            };

            this.ws.onerror = (error) => {
                console.error(`[WebSocket] Error:`, error);
                if (this.handlers.onError) {
                    this.handlers.onError(error);
                }
            };

            this.ws.onclose = (event) => {
                console.log(`[WebSocket] Closed:`, event);
                this.isConnecting = false;
                this.stopPingPong();
                
                if (this.handlers.onClose) {
                    this.handlers.onClose(event);
                }

                // Attempt reconnection if not intentionally closed
                if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnect();
                }
            };
        } catch (error) {
            console.error(`[WebSocket] Connection error:`, error);
            this.isConnecting = false;
            this.reconnect();
        }
    }

    reconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('[WebSocket] Cannot send, connection not open');
        }
    }

    startPingPong() {
        this.pingInterval = setInterval(() => {
            this.send({ type: 'ping' });
        }, 30000); // Ping every 30 seconds
    }

    stopPingPong() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    disconnect() {
        this.stopPingPong();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
    }

    handleMessage(data) {
        // Override in subclasses
    }

    on(event, handler) {
        this.handlers[event] = handler;
    }
}


/**
 * Notification WebSocket Client
 */
class NotificationWebSocket extends BaseWebSocket {
    constructor(authToken) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/notifications/?token=${authToken}`;
        super(url);
        this.notificationHandlers = [];
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('[Notifications] Connection established');
                break;
            
            case 'notification':
            case 'notification_message':
                this.notificationHandlers.forEach(handler => handler(data.data || data));
                break;
            
            case 'job_update':
            case 'application_update':
            case 'message_received':
                this.notificationHandlers.forEach(handler => handler(data));
                break;
            
            default:
                console.log('[Notifications] Unknown message type:', data.type);
        }
    }

    onNotification(handler) {
        this.notificationHandlers.push(handler);
    }

    markAsRead(notificationId) {
        this.send({
            type: 'mark_read',
            notification_id: notificationId
        });
    }
}


/**
 * Chat WebSocket Client
 */
class ChatWebSocket extends BaseWebSocket {
    constructor(conversationId, authToken) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/chat/${conversationId}/?token=${authToken}`;
        super(url);
        this.conversationId = conversationId;
        this.messageHandlers = [];
        this.typingHandlers = [];
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log(`[Chat] Connected to conversation ${data.conversation_id}`);
                break;
            
            case 'message':
                this.messageHandlers.forEach(handler => handler(data.data));
                break;
            
            case 'typing':
                this.typingHandlers.forEach(handler => handler(data));
                break;
            
            default:
                console.log('[Chat] Unknown message type:', data.type);
        }
    }

    onMessage(handler) {
        this.messageHandlers.push(handler);
    }

    onTyping(handler) {
        this.typingHandlers.push(handler);
    }

    sendTypingIndicator(isTyping = true) {
        this.send({
            type: 'typing',
            is_typing: isTyping
        });
    }
}


/**
 * Job Updates WebSocket Client
 */
class JobUpdatesWebSocket extends BaseWebSocket {
    constructor(location = null) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/jobs/`;
        super(url);
        this.location = location;
        this.jobHandlers = [];
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('[Jobs] Connection established');
                if (this.location) {
                    this.subscribeToLocation(this.location);
                }
                break;
            
            case 'new_job':
            case 'job_updated':
                this.jobHandlers.forEach(handler => handler(data));
                break;
            
            default:
                console.log('[Jobs] Unknown message type:', data.type);
        }
    }

    onJobUpdate(handler) {
        this.jobHandlers.push(handler);
    }

    subscribeToLocation(location) {
        this.send({
            type: 'subscribe_location',
            location: location
        });
    }
}


/**
 * WebSocket Manager - Manages all WebSocket connections
 */
class WebSocketManager {
    constructor() {
        this.connections = {};
    }

    createNotificationConnection(authToken) {
        if (!this.connections.notifications) {
            this.connections.notifications = new NotificationWebSocket(authToken);
            this.connections.notifications.connect();
        }
        return this.connections.notifications;
    }

    createChatConnection(conversationId, authToken) {
        const key = `chat_${conversationId}`;
        if (!this.connections[key]) {
            this.connections[key] = new ChatWebSocket(conversationId, authToken);
            this.connections[key].connect();
        }
        return this.connections[key];
    }

    createJobUpdatesConnection(location = null) {
        if (!this.connections.jobs) {
            this.connections.jobs = new JobUpdatesWebSocket(location);
            this.connections.jobs.connect();
        }
        return this.connections.jobs;
    }

    disconnectAll() {
        Object.values(this.connections).forEach(conn => conn.disconnect());
        this.connections = {};
    }

    disconnect(key) {
        if (this.connections[key]) {
            this.connections[key].disconnect();
            delete this.connections[key];
        }
    }
}

// Create global instance
window.wsManager = new WebSocketManager();
