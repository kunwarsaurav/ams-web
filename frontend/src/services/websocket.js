import { getClientId } from './api';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = {};
    const host = window.location.hostname || '127.0.0.1';
    const clientId = getClientId();
    this.url = `ws://${host}:8080/ws/${clientId}`;
    this.reconnectTimeout = 3000;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.type && this.listeners[data.type]) {
          this.listeners[data.type].forEach(callback => callback(data.data));
        }
      } catch (e) {
        console.error('Error parsing websocket message', e);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected. Reconnecting in 3s...');
      setTimeout(() => this.connect(), this.reconnectTimeout);
    };

    this.ws.onerror = (err) => {
      console.error('WebSocket error', err);
      this.ws.close();
    };
  }

  subscribe(type, callback) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(callback);
    return () => {
      this.listeners[type] = this.listeners[type].filter(cb => cb !== callback);
    };
  }
}

export const wsManager = new WebSocketManager();
