import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]               = useState(null);
  const [loading, setLoading]         = useState(true);
  const [locationId, setLocationId]   = useState(null);
  const [hasApiKey, setHasApiKey]     = useState(false);
  const [syncing, setSyncing]         = useState(false);
  const [lastSynced, setLastSynced]   = useState(null);
  const [syncVersion, setSyncVersion] = useState(0);
  const didInitialSync                = useRef(false);

  const extractLocation = (userData) => {
    const loc = userData?.locations?.[0];
    if (loc) {
      setLocationId(loc.id);
      setHasApiKey(!!loc.has_api_key);
    } else {
      setLocationId(null);
      setHasApiKey(false);
    }
  };

  const triggerSync = useCallback(async (locId) => {
    if (syncing) return;
    setSyncing(true);
    try {
      const id = locId || locationId;
      if (!id) return;
      await api.post(`/settings/maintainx-sync?location_id=${id}`, null, { timeout: 120000 });
      setLastSynced(new Date());
      setSyncVersion(v => v + 1);
    } catch { /* silently ignore */ } finally {
      setSyncing(false);
    }
  }, [syncing, locationId]);

  // On mount, validate stored token
  useEffect(() => {
    const token = localStorage.getItem('ts_token');
    if (!token) { setLoading(false); return; }
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    api.get('/auth/me')
      .then(res => {
        setUser(res.data);
        extractLocation(res.data);
      })
      .catch(() => {
        localStorage.removeItem('ts_token');
        delete api.defaults.headers.common['Authorization'];
      })
      .finally(() => setLoading(false));
  }, []);

  // Auto-sync once on load when we know the location has an API key
  useEffect(() => {
    if (hasApiKey && locationId && !didInitialSync.current) {
      didInitialSync.current = true;
      triggerSync(locationId);
    }
  }, [hasApiKey, locationId]); // eslint-disable-line react-hooks/exhaustive-deps

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('ts_token', res.data.token);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    setUser(res.data.user);
    extractLocation(res.data.user);
    return res.data.user;
  };

  const signup = async (name, email, password) => {
    const res = await api.post('/auth/signup', { name, email, password });
    localStorage.setItem('ts_token', res.data.token);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    setUser(res.data.user);
    extractLocation(res.data.user);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem('ts_token');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setLocationId(null);
    setHasApiKey(false);
    didInitialSync.current = false;
  };

  const refreshLocation = async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      extractLocation(res.data);
    } catch { /* ignore */ }
  };

  return (
    <AuthContext.Provider value={{
      user, loading, login, signup, logout,
      locationId, hasApiKey, refreshLocation,
      syncing, lastSynced, syncVersion, triggerSync,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
