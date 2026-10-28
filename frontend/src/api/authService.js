import api from './axios.js';
export const authService = {
  register: async d => (await api.post('/auth/register', { email:d.email, full_name:d.fullName, password:d.password })).data,
  login:    async d => (await api.post('/auth/login', d)).data,
  me:       async () => (await api.get('/auth/me')).data,
};
