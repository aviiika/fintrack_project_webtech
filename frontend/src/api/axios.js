import axios from 'axios';
const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const KEY = 'fintrack_token';
export const token = {
  get: () => localStorage.getItem(KEY),
  set: (t) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
};
const api = axios.create({ baseURL: BASE, timeout: 30000 });
api.interceptors.request.use(c => { const t = token.get(); if (t) c.headers.Authorization = `Bearer ${t}`; return c; });
api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    token.clear();
    if (!window.location.pathname.startsWith('/login')) window.location.assign('/login');
  }
  return Promise.reject({ status: err.response?.status,
    message: err.response?.data?.detail || err.message || 'Something went wrong' });
});
export default api;
