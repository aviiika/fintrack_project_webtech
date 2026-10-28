import api from './axios.js';

/** Loan / EMI endpoints. Outstanding balance is derived server-side on every read. */
export const loanService = {
  list: async () => (await api.get('/loans')).data,
  add: async (payload) => (await api.post('/loans', payload)).data,
  remove: async (id) => (await api.delete(`/loans/${id}`)).data,
};
