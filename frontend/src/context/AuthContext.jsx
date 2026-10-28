import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authService } from '../api/authService.js';
import { token } from '../api/axios.js';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  useEffect(() => {
    let alive = true;
    (async () => {
      if (!token.get()) { setInitializing(false); return; }
      try { const u = await authService.me(); if (alive) setUser(u); }
      catch { token.clear(); }
      finally { if (alive) setInitializing(false); }
    })();
    return () => { alive = false; };
  }, []);
  const login = useCallback(async c => { const d = await authService.login(c); token.set(d.access_token); setUser(d.user); return d.user; }, []);
  const register = useCallback(async i => { const d = await authService.register(i); token.set(d.access_token); setUser(d.user); return d.user; }, []);
  const logout = useCallback(() => { token.clear(); setUser(null); }, []);
  const value = useMemo(() => ({ user, isAuthenticated: !!user, initializing, login, register, logout }), [user, initializing, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const c = useContext(AuthContext); if (!c) throw new Error('useAuth outside provider'); return c; }
