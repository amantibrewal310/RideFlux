import type { WSMessage } from "../types/ws";

type MessageHandler = (msg: WSMessage) => void;

/**
 * WebSocket client singleton with:
 * - Auto-reconnect with exponential back-off (max 10 attempts, cap 30 s)
 * - Heartbeat ping every 30 s
 * - Typed message callback
 */
class WebSocketClient {
  /* ---------- singleton ---------- */
  private static instance: WebSocketClient;

  static getInstance(): WebSocketClient {
    if (!WebSocketClient.instance) {
      WebSocketClient.instance = new WebSocketClient();
    }
    return WebSocketClient.instance;
  }

  /* ---------- internal state ---------- */
  private ws: WebSocket | null = null;
  private url = "";
  private messageHandler: MessageHandler | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private _connected = false;

  private constructor() {} // enforce singleton

  /* ---------- public API ---------- */

  get connected(): boolean {
    return this._connected;
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandler = handler;
  }

  connect(url: string): void {
    this.url = url;
    this.createConnection();
  }

  disconnect(): void {
    this.clearTimers();
    if (this.ws) {
      this.ws.onclose = null; // prevent reconnect on intentional close
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  /* ---------- internals ---------- */

  private createConnection(): void {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this._connected = true;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        this.messageHandler?.(msg);
      } catch {
        // ignore non-JSON frames
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this.clearTimers();
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => this.createConnection(), delay);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 30_000);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

export default WebSocketClient;
