/**
 * WebSocket Service for Admin Dashboard
 * Real-time updates using Socket.IO
 */

import { io } from 'socket.io-client';

const WEBSOCKET_URL = 'http://localhost:8888';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    console.log(`Connecting to WebSocket: ${WEBSOCKET_URL}`);

    this.socket = io(WEBSOCKET_URL, {
      path: '/ws/socket.io',  // Custom path where Socket.IO is mounted
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000
    });

    this.setupEventHandlers();
  }

  /**
   * Setup Socket.IO event handlers
   */
  setupEventHandlers() {
    // Connection events
    this.socket.on('connect', () => {
      console.log('✅ Admin Dashboard WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected');
    });

    this.socket.on('disconnect', () => {
      console.log('❌ Admin Dashboard WebSocket disconnected');
      this.emit('disconnected');
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('error', error);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`✅ WebSocket reconnected after ${attemptNumber} attempts`);
      this.emit('reconnected', attemptNumber);
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('❌ WebSocket reconnection error:', error);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('❌ WebSocket reconnection failed');
      this.emit('reconnect_failed');
    });

    // Backend events
    this.socket.on('log_entry', (data) => {
      console.log('New log entry:', data);
      this.emit('log_entry', data);
    });

    this.socket.on('task_update', (data) => {
      console.log('Task update:', data);
      this.emit('task_update', data);
    });

    this.socket.on('session_start', (data) => {
      console.log('Session started:', data);
      this.emit('session_start', data);
    });

    this.socket.on('session_end', (data) => {
      console.log('Session ended:', data);
      this.emit('session_end', data);
    });

    this.socket.on('user_activity', (data) => {
      console.log('User activity:', data);
      this.emit('user_activity', data);
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  /**
   * Subscribe to event
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    };
  }

  /**
   * Emit event to listeners
   */
  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  /**
   * Send message to server
   */
  send(event, data) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.error('WebSocket not connected');
    }
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.socket?.connected || false;
  }
}

// Export singleton instance
export const websocket = new WebSocketService();
