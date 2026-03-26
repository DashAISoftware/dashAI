import { useCallback, useEffect, useRef, useState } from "react";

export function useHardwareMonitor(enabled) {
  const [stats, setStats] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

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
      wsRef.current = null;
      if (enabled) {
        reconnectTimeout.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = (error) => {
      console.error("Hardware WebSocket error:", error);
    };

    wsRef.current = ws;
  }, [enabled]);

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, connect]);

  return { stats, connected };
}
