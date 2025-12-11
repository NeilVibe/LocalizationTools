/**
 * WebSocket Service for LocaNext
 * Real-time updates using Socket.IO
 */

import { io } from 'socket.io-client';
import { get } from 'svelte/store';
import { serverUrl, isConnected } from '$lib/stores/app.js';

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
    const url = get(serverUrl);

    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    console.log(`Connecting to WebSocket: ${url}`);

    this.socket = io(url, {
      path: '/ws/socket.io',  // Server Socket.IO path
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
      console.log('WebSocket connected');
      isConnected.set(true);
      this.reconnectAttempts = 0;
      this.emit('connected');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      isConnected.set(false);
      this.emit('disconnected');
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('error', error);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
      isConnected.set(true);
      this.emit('reconnected', attemptNumber);
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('WebSocket reconnection error:', error);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('WebSocket reconnection failed');
      isConnected.set(false);
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

    // Progress tracking events
    this.socket.on('operation_start', (data) => {
      console.log('Operation started:', data);
      this.emit('operation_start', data);
    });

    this.socket.on('progress_update', (data) => {
      console.log('Progress update:', data);
      this.emit('progress_update', data);
    });

    this.socket.on('operation_complete', (data) => {
      console.log('Operation complete:', data);
      this.emit('operation_complete', data);
    });

    this.socket.on('operation_failed', (data) => {
      console.log('Operation failed:', data);
      this.emit('operation_failed', data);
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      isConnected.set(false);
    }
  }

  /**
   * Subscribe to event
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);

      // Register Socket.IO listener for this event type (first time only)
      // This ensures server events are relayed to our internal listeners
      if (this.socket) {
        this.socket.on(event, (data) => {
          this.emit(event, data);
        });
      }
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
