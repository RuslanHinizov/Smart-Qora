import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { readToken } from "./client";
import { keys } from "./queries";
import type { EventRow, LiveMessage, Totals } from "./types";

type SocketStatus = "connecting" | "open" | "closed";

const MAX_BACKOFF = 30_000;

/**
 * One WebSocket to /ws/live. Patches the react-query cache on push messages
 * (no refetch per crossing). Exponential backoff with jitter and no cap on
 * attempts — a farm box may be offline for a long time.
 */
export function useLiveSocket() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const attemptRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let disposed = false;

    const connect = () => {
      const token = readToken();
      if (!token) {
        setStatus("closed");
        return;
      }
      setStatus("connecting");
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${scheme}://${window.location.host}/ws/live?token=${encodeURIComponent(token)}`,
      );

      socket.onopen = () => {
        attemptRef.current = 0;
        setStatus("open");
      };

      socket.onmessage = (event) => {
        let message: LiveMessage;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (message.type === "statistics") {
          qc.setQueryData<Totals>(keys.statsToday, {
            total_in: message.in,
            total_out: message.out,
            current: message.current,
          });
          qc.setQueryData(keys.status, (prev: Record<string, unknown> | undefined) =>
            prev ? { ...prev, camera: message.camera, ai: message.ai } : prev,
          );
        } else if (message.type === "event") {
          qc.setQueriesData<{ rows: EventRow[]; total: number }>(
            { queryKey: ["events"] },
            (page) =>
              page
                ? { rows: [message.event, ...page.rows].slice(0, 200), total: page.total + 1 }
                : page,
          );
        }
      };

      socket.onerror = () => socket?.close();

      socket.onclose = () => {
        if (disposed) return;
        setStatus("closed");
        const attempt = (attemptRef.current += 1);
        const base = Math.min(MAX_BACKOFF, 1000 * 2 ** Math.min(attempt, 5));
        const delay = base / 2 + Math.random() * (base / 2);
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [qc]);

  return status;
}
