import api, { token } from './axios.js';

/** Dashboard, transactions, imports, budgets, reports — the core finance endpoints. */
export const financeService = {
  // ── Dashboard / reports ────────────────────────────────────────────────────
  dashboard: async (month, bank) =>
    (await api.get('/dashboard', { params: { month, ...(bank && bank !== 'all' ? { bank } : {}) } })).data,
  annual: async (year) => (await api.get(`/reports/annual/${year}`)).data,

  // ── Transactions ───────────────────────────────────────────────────────────
  transactions: async (params) => (await api.get('/transactions', { params })).data,
  categories: async () => (await api.get('/transactions/categories')).data.categories,
  months: async () => (await api.get('/transactions/months')).data.months,
  updateTransaction: async (id, payload) => (await api.patch(`/transactions/${id}`, payload)).data,
  deleteTransaction: async (id) => (await api.delete(`/transactions/${id}`)).data,

  // ── Import ─────────────────────────────────────────────────────────────────
  banks: async () => (await api.get('/import/banks')).data.banks,
  importHistory: async () => (await api.get('/import/history')).data,
  upload: async (file, bank, onProgress) => {
    const form = new FormData();
    form.append('file', file);
    form.append('bank', bank);
    const res = await api.post('/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
    return res.data;
  },

  // ── Budgets ────────────────────────────────────────────────────────────────
  budgets: async (month) => (await api.get('/budgets', { params: { month } })).data,
  createBudget: async (payload) => (await api.post('/budgets', payload)).data,
  updateBudget: async (id, payload) => (await api.patch(`/budgets/${id}`, payload)).data,
  deleteBudget: async (id) => (await api.delete(`/budgets/${id}`)).data,
};

/**
 * Triggers a file download for an authenticated endpoint.
 *
 * A plain <a href> can't carry the JWT, so fetch the bytes with the token
 * attached, wrap them in a blob URL, and click a synthetic link. The blob URL is
 * revoked immediately after -- otherwise every export leaks a few MB of memory
 * that the browser holds until the tab closes.
 */
export async function downloadFile(path, filename, params = {}) {
  const res = await api.get(path, { params, responseType: 'blob' });
  const url = window.URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export { token };
