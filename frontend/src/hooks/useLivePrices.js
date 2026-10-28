import { useEffect, useRef, useState } from 'react';
import { buildPricesWsUrl } from '../api/portfolioService.js';

/**
 * Subscribes to the /ws/prices stream and keeps the latest price tick per symbol
 * in state. Falls back gracefully: if the socket can't connect or drops, the page
 * still works off whatever /portfolio/summary last returned — this hook only adds
 * the "live" layer on top.
 *
 * Reconnects with a fixed backoff rather than giving up after one failure, since a
 * dev server restart or a brief network blip shouldn't require a page reload.
 */
export function useLivePrices(enabled = true) {
  const [prices, setPrices] = useState({});
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const ws = new WebSocket(buildPricesWsUrl());
      socketRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'price_update') setPrices(msg.prices || {});
        } catch { /* ignore malformed frame */ }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) retryRef.current = setTimeout(connect, 4000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      cancelled = true;
      if (retryRef.current) clearTimeout(retryRef.current);
      socketRef.current?.close();
    };
  }, [enabled]);

  return { prices, connected };
}
