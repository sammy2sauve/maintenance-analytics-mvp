import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { Copy, Check, Users, Bell, RefreshCw, Unlink, Link, Info } from 'lucide-react';

function DemoNotice({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="mb-4 flex items-start gap-2.5 p-3 bg-indigo-500/10 border border-indigo-500/25 rounded-lg">
      <Info className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-indigo-300 leading-relaxed flex-1">{message}</p>
      <button onClick={onDismiss} className="text-indigo-400/50 hover:text-indigo-300 text-xs ml-1">✕</button>
    </div>
  );
}


function authHeaders() {
  const token = localStorage.getItem('ts_token');
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}


function RoleBadge({ role }) {
  const styles = {
    owner:  'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30',
    admin:  'bg-amber-500/20 text-amber-300 border border-amber-500/30',
    viewer: 'bg-slate-700/50 text-slate-400 border border-slate-600/30',
  };
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full capitalize ${styles[role] || styles.viewer}`}>
      {role}
    </span>
  );
}

function SeatBar({ used, limit, tier }) {
  const pct   = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const color = pct >= 100 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-slate-400">
          <span className="text-white font-medium">{used}</span>
          {limit
            ? <> of <span className="text-white font-medium">{limit}</span> seats used</>
            : ' seats used (unlimited)'}
        </span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wide">{tier}</span>
      </div>
      {limit && (
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-300 ${color}`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

const DEMO_TEAM = {
  members: [
    { id: 'demo-you', name: 'Demo Account (You)', email: 'support@truesignalapp.com', role: 'owner' },
    { id: 'demo-1',   name: 'Alex Rivera',        email: 'alex.rivera@meridianmedical.com', role: 'admin' },
    { id: 'demo-2',   name: 'Sarah Chen',          email: 'sarah.chen@meridianmedical.com',  role: 'viewer' },
    { id: 'demo-3',   name: 'Marcus Williams',     email: 'm.williams@meridianmedical.com',  role: 'viewer' },
  ],
  seat_usage: { used: 4, limit: 10, tier: 'Pro' },
};

function TeamSection({ currentUserId, currentUserRole, isDemo }) {
  const [team, setTeam]         = useState(isDemo ? DEMO_TEAM : null);
  const [codes, setCodes]       = useState([]);
  const [genRole, setGenRole]   = useState('viewer');
  const [genExpiry, setGenExpiry] = useState(7);
  const [generating, setGenerating] = useState(false);
  const [newCode, setNewCode]   = useState(null);
  const [copied, setCopied]     = useState(false);
  const [removing, setRemoving] = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [teamError, setTeamError] = useState('');
  const [demoMsg, setDemoMsg]   = useState('');

  const fetchTeam = async () => {
    try {
      const [teamRes, codesRes] = await Promise.all([
        api.get('/invites/team'),
        api.get('/invites'),
      ]);
      setTeam(teamRes.data);
      setCodes(codesRes.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { if (!isDemo) fetchTeam(); }, []);

  const generateCode = async () => {
    if (isDemo) {
      setDemoMsg('This is a demo account. In your account, you can generate invite codes to add teammates — set their role and expiry, then share the link.');
      return;
    }
    setGenerating(true); setTeamError(''); setNewCode(null);
    try {
      const res = await api.post('/invites/generate', { role: genRole, expires_days: genExpiry });
      setNewCode(res.data.code);
      fetchTeam();
    } catch (err) {
      setTeamError(err.response?.data?.detail || 'Failed to generate code');
    } finally {
      setGenerating(false);
    }
  };

  const copyCode = () => {
    if (!newCode) return;
    navigator.clipboard.writeText(newCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const revokeCode = async (code) => {
    setRevoking(code);
    try {
      await api.delete(`/invites/${code}`);
      setCodes(prev => prev.filter(c => c.code !== code));
      if (newCode === code) setNewCode(null);
    } catch { /* ignore */ } finally {
      setRevoking(null);
    }
  };

  const removeMember = async (userId) => {
    if (isDemo) {
      setDemoMsg('This is a demo account. In your account, removing a member revokes their access and frees up a seat.');
      return;
    }
    setRemoving(userId); setTeamError('');
    try {
      await api.delete(`/invites/team/${userId}`);
      fetchTeam();
    } catch (err) {
      setTeamError(err.response?.data?.detail || 'Failed to remove member');
    } finally {
      setRemoving(null);
    }
  };

  const isOwner = currentUserRole === 'owner';

  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-6 mb-4">
      <div className="flex items-center gap-2 mb-5">
        <Users className="w-4 h-4 text-indigo-400" />
        <h2 className="text-base font-semibold text-white">Team</h2>
        {isDemo && <span className="ml-auto text-[10px] text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">Demo</span>}
      </div>

      <DemoNotice message={demoMsg} onDismiss={() => setDemoMsg('')} />

      {!team ? (
        <p className="text-xs text-slate-500 animate-pulse">Loading team…</p>
      ) : (
        <>
          <SeatBar {...team.seat_usage} />

          {/* Member list */}
          <div className="mt-5 space-y-1">
            {team.members.map(m => (
              <div key={m.id} className="flex items-center gap-3 py-2.5 border-b border-slate-700/30 last:border-0">
                <div className="w-7 h-7 rounded-full bg-indigo-900/60 flex items-center justify-center text-xs font-bold text-indigo-300 flex-shrink-0">
                  {m.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">{m.name}</p>
                  <p className="text-xs text-slate-500 truncate">{m.email}</p>
                </div>
                <RoleBadge role={m.role} />
                {isOwner && m.id !== currentUserId && (
                  <button
                    onClick={() => removeMember(m.id)}
                    disabled={removing === m.id}
                    className="text-xs text-red-400/50 hover:text-red-400 transition-colors ml-1 disabled:opacity-40"
                  >
                    {removing === m.id ? '…' : 'Remove'}
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Generate invite code */}
          <div className="mt-5 pt-4 border-t border-slate-700/30">
            <p className="text-xs font-medium text-slate-300 mb-3">Generate Invite Code</p>
            <div className="flex gap-2 flex-wrap items-center">
              <select
                value={genRole}
                onChange={e => setGenRole(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="viewer">Viewer</option>
                {isOwner && <option value="admin">Admin</option>}
              </select>
              <select
                value={genExpiry}
                onChange={e => setGenExpiry(Number(e.target.value))}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value={1}>Expires in 1 day</option>
                <option value={7}>Expires in 7 days</option>
                <option value={30}>Expires in 30 days</option>
              </select>
              <button
                onClick={generateCode}
                disabled={generating}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                {generating ? 'Generating…' : 'Generate'}
              </button>
            </div>

            {newCode && (
              <div className="mt-3 flex items-center gap-2 bg-slate-800 border border-indigo-500/30 rounded-lg px-3 py-2">
                <code className="text-xs text-indigo-300 flex-1 font-mono break-all">{newCode}</code>
                <button onClick={copyCode} className="text-slate-400 hover:text-white transition-colors flex-shrink-0 ml-1" title="Copy">
                  {copied
                    ? <Check className="w-3.5 h-3.5 text-emerald-400" />
                    : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            )}
          </div>

          {/* Active codes */}
          {codes.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-700/30">
              <p className="text-xs font-medium text-slate-300 mb-2">Active Invite Codes</p>
              <div className="space-y-2">
                {codes.map(c => (
                  <div key={c.code} className="flex items-center gap-2 text-xs">
                    <code className="text-slate-400 font-mono flex-1 truncate">{c.code.slice(0, 18)}…</code>
                    <RoleBadge role={c.role} />
                    {c.expires_at && (
                      <span className="text-slate-600 text-[10px]">
                        exp {new Date(c.expires_at).toLocaleDateString()}
                      </span>
                    )}
                    <button
                      onClick={() => revokeCode(c.code)}
                      disabled={revoking === c.code}
                      className="text-red-400/50 hover:text-red-400 transition-colors disabled:opacity-40"
                    >
                      {revoking === c.code ? '…' : 'Revoke'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {teamError && <p className="mt-3 text-xs text-red-400">{teamError}</p>}
        </>
      )}
    </div>
  );
}

const SETTINGS_ALERT_RULES = [
  { key: 'any_critical',  label: 'Critical asset detected',         description: 'Alert when any asset reaches CRITICAL risk level' },
  { key: 'high_count',    label: 'High risk spike',                  description: 'Alert when HIGH+CRITICAL assets exceed 5' },
  { key: 'no_wo_days',    label: 'Asset with no maintenance 90+ days', description: 'Alert when an asset has no work order for 90+ days' },
  { key: 'savings_opportunity', label: 'Savings opportunity > $10k', description: 'Alert when total PM savings opportunity exceeds $10,000' },
];

function AlertsSection({ locationId }) {
  const [rules, setRules] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!locationId) return;
    api.get('/alerts/rules', { params: { location_id: locationId } })
      .then(res => {
        const map = {};
        (res.data.rules || []).forEach(r => { map[r.rule_key] = r.enabled; });
        setRules(map);
      })
      .catch(() => {});
  }, [locationId]);

  const toggle = async (key) => {
    const next = { ...rules, [key]: !rules[key] };
    setRules(next);
    setSaving(true);
    try {
      const defaultThresholds = { high_count: 5, no_wo_days: 90, savings_opportunity: 10000 };
      await api.post('/alerts/rules', {
        location_id: locationId,
        rules: SETTINGS_ALERT_RULES.map(r => ({
          rule_key:  r.key,
          threshold: defaultThresholds[r.key] ?? null,
          channel:   'Email',
          frequency: 'Immediately',
          enabled:   next[r.key] ?? false,
        })),
      });
    } catch { /* silently revert */ }
    setSaving(false);
  };

  return (
    <div className="space-y-0">
      {SETTINGS_ALERT_RULES.map(alert => (
        <div key={alert.key} className="flex items-start justify-between gap-4 py-3 border-b border-slate-700/30 last:border-0">
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white">{alert.label}</p>
            <p className="text-xs text-slate-500 mt-0.5">{alert.description}</p>
          </div>
          <button
            onClick={() => toggle(alert.key)}
            disabled={saving}
            className={`relative flex-shrink-0 w-10 h-5 rounded-full transition-colors duration-200 disabled:opacity-60 ${rules[alert.key] ? 'bg-indigo-600' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${rules[alert.key] ? 'translate-x-5' : ''}`} />
          </button>
        </div>
      ))}
    </div>
  );
}

function FaciliWorksSection({ locationId, isOwnerOrAdmin, refreshLocation, isDemo }) {
  const [connected, setConnected]   = useState(false);
  const [loading, setLoading]       = useState(true);
  const [baseUrl, setBaseUrl]       = useState('');
  const [apiKey, setApiKey]         = useState('');
  const [saving, setSaving]         = useState(false);
  const [syncing, setSyncing]       = useState(false);
  const [error, setError]           = useState('');
  const [syncResult, setSyncResult] = useState(null);
  const [demoMsg, setDemoMsg]       = useState('');

  useEffect(() => {
    api.get('/settings/faciliworks-key', { params: { location_id: locationId } })
      .then(r => setConnected(r.data.connected))
      .catch(() => setConnected(false))
      .finally(() => setLoading(false));
  }, [locationId]);

  const connect = async () => {
    if (!baseUrl.trim() || !apiKey.trim()) {
      setError('Both fields are required.');
      return;
    }
    setSaving(true); setError(''); setSyncResult(null);
    try {
      await api.post('/settings/faciliworks-key', {
        base_url: baseUrl.trim(),
        api_key: apiKey.trim(),
        location_id: locationId,
      });
      setConnected(true);
      setBaseUrl(''); setApiKey('');
      await refreshLocation();
      // Auto-sync immediately after connecting
      setSyncing(true);
      try {
        const r = await api.post('/settings/faciliworks-sync', null, { params: { location_id: locationId }, timeout: 120000 });
        setSyncResult(r.data);
      } catch (err) {
        // Backend deletes the key on sync failure — reflect that in UI
        setConnected(false);
        await refreshLocation();
        setError(err.response?.data?.detail || 'Sync failed. Check your URL and API key.');
      } finally {
        setSyncing(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save credentials.');
    } finally {
      setSaving(false);
    }
  };

  const disconnect = async () => {
    if (isDemo) {
      setDemoMsg('This is a demo account connected to sample Meridian Medical Center data. In your account, disconnecting would unlink your CMMS and let you reconnect with a new API token.');
      return;
    }
    setSaving(true); setError(''); setSyncResult(null);
    try {
      await api.delete('/settings/faciliworks-key', { params: { location_id: locationId } });
      setConnected(false);
    } catch { /* ignore */ } finally {
      setSaving(false);
    }
  };

  const syncNow = async () => {
    setSyncing(true); setError(''); setSyncResult(null);
    try {
      const r = await api.post('/settings/faciliworks-sync', null, { params: { location_id: locationId }, timeout: 120000 });
      setSyncResult(r.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <p className="text-xs text-slate-500 animate-pulse">Checking connection…</p>;

  return (
    <div>
      <DemoNotice message={demoMsg} onDismiss={() => setDemoMsg('')} />
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-white">FaciliWorks</h2>
          <p className="text-xs text-slate-400 mt-0.5">Sync work orders and assets from FaciliWorks into TrueSignal.</p>
        </div>
        <div className={`flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full border flex-shrink-0 ml-4 ${
          connected
            ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
            : 'text-slate-400 bg-slate-800/60 border-slate-700/40'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400' : 'bg-slate-600'}`} />
          {connected ? 'Connected' : 'Not connected'}
        </div>
      </div>

      {connected ? (
        <div className="space-y-3">
          <div className="flex gap-2">
            {isOwnerOrAdmin && (
              <>
                <button
                  onClick={syncNow}
                  disabled={syncing}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                  {syncing ? 'Syncing…' : 'Sync Now'}
                </button>
                <button
                  onClick={disconnect}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 border border-slate-700/50"
                >
                  <Unlink className="w-3.5 h-3.5" />
                  Disconnect
                </button>
              </>
            )}
          </div>
          {syncResult && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300 space-y-0.5">
              <p>Sync complete — {syncResult.inserted} new, {syncResult.updated} updated</p>
              {syncResult.predictions_stored > 0 && (
                <p className="text-slate-400">{syncResult.predictions_stored} predictions refreshed · {syncResult.implemented} suggestions marked implemented</p>
              )}
            </div>
          )}
        </div>
      ) : isOwnerOrAdmin ? (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">FaciliWorks Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
              placeholder="https://your-site.faciliworks.com"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="••••••••••••••••"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <button
            onClick={connect}
            disabled={saving || syncing}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <Link className="w-3.5 h-3.5" />
            {saving ? 'Connecting…' : syncing ? 'Syncing data…' : 'Connect FaciliWorks'}
          </button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">Contact your admin to connect FaciliWorks.</p>
      )}

      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
    </div>
  );
}

export default function Settings() {
  const { user, role, isOwnerOrAdmin, isDemo, locationId, refreshLocation } = useAuth();

  return (
    <div className="w-full h-full px-6 py-6 overflow-y-auto">
      <h1 className="text-xl font-semibold text-white mb-1">Settings</h1>
      <p className="text-sm text-slate-400 mb-6">Manage your platform connection, team, and alert preferences.</p>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Left: Platform + Team combined */}
        <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-6">

          {/* FaciliWorks connection */}
          <FaciliWorksSection locationId={locationId} isOwnerOrAdmin={isOwnerOrAdmin} refreshLocation={refreshLocation} isDemo={isDemo} />

          {/* Divider into Team */}
          {isOwnerOrAdmin && user && (
            <>
              <div className="border-t border-slate-700/40 my-6" />
              <TeamSection currentUserId={user.id} currentUserRole={role} isDemo={isDemo} />
            </>
          )}
        </div>

        {/* Right col: Alerts */}
        <div className="space-y-6">

        {/* Alerts */}
        <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-5">
            <Bell className="w-4 h-4 text-amber-400" />
            <h2 className="text-base font-semibold text-white">Alerts</h2>
            <span className="ml-auto text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">Email active</span>
          </div>
          <AlertsSection locationId={locationId} />
          <p className="text-xs text-slate-600 mt-4">Alerts are sent to your account email after each sync. Use "Notify Me" on any page for custom thresholds.</p>
        </div>

        {/* Future integrations placeholder */}
        <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-6 opacity-50">
          <h2 className="text-base font-semibold text-slate-400">More integrations coming soon</h2>
          <p className="text-xs text-slate-500 mt-1">Limble, UpKeep, Fiix</p>
        </div>
        </div> {/* end right col */}
        </div> {/* end grid */}
    </div>
  );
}
