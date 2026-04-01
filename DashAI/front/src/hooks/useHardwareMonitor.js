import { useCallback, useEffect, useRef, useState } from "react";

export function useHardwareMonitor(enabled) {
  const [stats, setStats] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);
  const enabledRef = useRef(enabled);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
  }, []);

  const closeSocket = useCallback(() => {
    if (!wsRef.current) {
      return;
    }

    // Remove handlers to avoid reconnect scheduling from intentional closes.
    wsRef.current.onopen = null;
    wsRef.current.onmessage = null;
    wsRef.current.onclose = null;
    wsRef.current.onerror = null;
    wsRef.current.close();
    wsRef.current = null;
  }, []);

  const connect = useCallback(() => {
    if (!enabledRef.current) {
      return;
    }

    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    clearReconnectTimeout();

    const apiUrl = process.env.REACT_APP_API_URL || `${window.location.origin}`;
    let wsUrl;
    try {
      wsUrl = new URL("api/v1/hardware/ws", apiUrl);
    } catch (e) {
      console.error("Invalid WebSocket base URL:", apiUrl);
      return;
    }

    if (wsUrl.protocol === "http:") {
      wsUrl.protocol = "ws:";
    } else if (wsUrl.protocol === "https:") {
      wsUrl.protocol = "wss:";
    }

    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStats(data);
      } catch (e) {
        console.error("Failed to parse hardware stats:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (enabledRef.current) {
        clearReconnectTimeout();
        reconnectTimeout.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = (error) => {
      console.error("Hardware WebSocket error:", error);
    };
  }, [clearReconnectTimeout]);

  useEffect(() => {
    enabledRef.current = enabled;

    if (enabled) {
      connect();
    } else {
      setConnected(false);
      clearReconnectTimeout();
      closeSocket();
    }
  }, [enabled, connect, clearReconnectTimeout, closeSocket]);

  useEffect(() => {
    return () => {
      enabledRef.current = false;
      clearReconnectTimeout();
      closeSocket();
    };
  }, [clearReconnectTimeout, closeSocket]);

  return { stats, connected };
}
