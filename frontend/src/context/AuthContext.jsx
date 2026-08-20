import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]               = useState(null);
  const [loading, setLoading]         = useState(true);
  const [locationId, setLocationId]   = useState(null);
  const [hasApiKey, setHasApiKey]     = useState(false);
  const [role, setRole]               = useState(null);
  const [plan, setPlan]               = useState(null);
  const [trialDaysLeft, setTrialDaysLeft] = useState(null);
  const [syncing, setSyncing]         = useState(false);
  const [lastSynced, setLastSynced]   = useState(null);
  const [syncVersion, setSyncVersion] = useState(0);
  const didInitialSync                = useRef(false);

  const extractLocation = (userData) => {
    const loc = userData?.locations?.[0];
    if (loc) {
      setLocationId(loc.id);
      setHasApiKey(!!loc.has_api_key);
      setRole(loc.access_role || null);
      setPlan(loc.plan || null);
      setTrialDaysLeft(loc.trial_days_left ?? null);
    } else {
      setLocationId(null);
      setHasApiKey(false);
      setRole(null);
      setPlan(null);
      setTrialDaysLeft(null);
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

  // Re-fetch all page data when the user switches back to this tab
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        setSyncVersion(v => v + 1);
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, []);

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('ts_token', res.data.token);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    setUser(res.data.user);
    extractLocation(res.data.user);
    return res.data.user;
  };

  const signup = async (name, email, password, { orgName, inviteCode } = {}) => {
    const body = { name, email, password };
    if (inviteCode) body.invite_code = inviteCode;
    else if (orgName) body.org_name = orgName;
    const res = await api.post('/auth/signup', body);
    localStorage.setItem('ts_token', res.data.token);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    setUser(res.data.user);
    extractLocation(res.data.user);
    return res.data.user;
  };

  const loginAsDemo = async () => {
    const res = await api.post('/auth/demo', null, { timeout: 45000 });
    localStorage.setItem('ts_token', res.data.token);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    setUser(res.data.user);
    extractLocation(res.data.user);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem('ts_token');
    localStorage.removeItem('ts_overview_cache');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setLocationId(null);
    setHasApiKey(false);
    setRole(null);
    setPlan(null);
    setTrialDaysLeft(null);
    didInitialSync.current = false;
  };

  const refreshLocation = async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      extractLocation(res.data);
    } catch { /* ignore */ }
  };

  const isOwnerOrAdmin = role === 'owner' || role === 'admin';
  const isDemo = locationId === 3;
  const trialActive = plan === 'trial' && trialDaysLeft !== null && trialDaysLeft > 0;
  const trialExpired = plan === 'trial' && trialDaysLeft !== null && trialDaysLeft <= 0;

  return (
    <AuthContext.Provider value={{
      user, loading, login, signup, logout, loginAsDemo,
      locationId, hasApiKey, refreshLocation,
      role, isOwnerOrAdmin, isDemo,
      plan, trialDaysLeft, trialActive, trialExpired,
      syncing, lastSynced, syncVersion, triggerSync,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
