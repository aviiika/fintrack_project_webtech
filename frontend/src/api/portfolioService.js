import api, { token } from './axios.js';

/** Portfolio REST endpoints — powers the Portfolio page. */
export const portfolioService = {
  list: async () => (await api.get('/portfolio/holdings')).data,
  add: async (payload) => (await api.post('/portfolio/holdings', payload)).data,
  remove: async (id) => (await api.delete(`/portfolio/holdings/${id}`)).data,
  summary: async () => (await api.get('/portfolio/summary')).data,
};

/** Builds the ws:// / wss:// URL for the live price stream, carrying the JWT as a
 * query param since a WebSocket handshake can't set an Authorization header. */
export function buildPricesWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const base = import.meta.env.VITE_WS_BASE_URL || `${proto}://${window.location.host}/api/v1`;
  return `${base}/ws/prices?token=${encodeURIComponent(token.get() || '')}`;
}
