import api from './axios.js';

/** Net worth endpoints — cash + investments - outstanding liabilities. */
export const networthService = {
  summary: async () => (await api.get('/networth')).data,
  history: async () => (await api.get('/networth/history')).data,
  /** Takes today's snapshot on demand — same action the nightly scheduler job runs. */
  snapshot: async () => (await api.post('/networth/snapshot')).data,
};
