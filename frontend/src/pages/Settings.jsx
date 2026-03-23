import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { Copy, Check, Users } from 'lucide-react';

const API = 'http://localhost:8000';

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

function TeamSection({ currentUserId, currentUserRole }) {
  const [team, setTeam]         = useState(null);
  const [codes, setCodes]       = useState([]);
  const [genRole, setGenRole]   = useState('viewer');
  const [genExpiry, setGenExpiry] = useState(7);
  const [generating, setGenerating] = useState(false);
  const [newCode, setNewCode]   = useState(null);
  const [copied, setCopied]     = useState(false);
  const [removing, setRemoving] = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [teamError, setTeamError] = useState('');

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

  useEffect(() => { fetchTeam(); }, []);

  const generateCode = async () => {
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
      </div>

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

export default function Settings() {
  const { refreshLocation, user, role, isOwnerOrAdmin } = useAuth();
  const [connected, setConnected] = useState(null);
  const [apiKey, setApiKey]       = useState('');
  const [saving, setSaving]       = useState(false);
  const [removing, setRemoving]   = useState(false);
  const [syncing, setSyncing]     = useState(false);
  const [error, setError]         = useState('');
  const [success, setSuccess]     = useState('');

  useEffect(() => {
    fetch(`${API}/settings/maintainx-key`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setConnected(d.connected))
      .catch(() => setConnected(false));
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setError(''); setSuccess('');
    if (!apiKey.trim()) return setError('Paste your MaintainX API key above.');
    setSaving(true);
    try {
      const r = await fetch(`${API}/settings/maintainx-key`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ api_key: apiKey }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Failed to save');
      setConnected(true);
      setApiKey('');
      setSuccess('MaintainX connected successfully.');
      refreshLocation();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSync() {
    setError(''); setSuccess('');
    setSyncing(true);
    try {
      const r = await fetch(`${API}/settings/maintainx-sync`, {
        method: 'POST',
        headers: authHeaders(),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Sync failed');
      setSuccess(`Sync complete — ${d.inserted} new, ${d.updated} updated.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  async function handleRemove() {
    setError(''); setSuccess('');
    setRemoving(true);
    try {
      await fetch(`${API}/settings/maintainx-key`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setConnected(false);
      setSuccess('MaintainX disconnected.');
      refreshLocation();
    } catch {
      setError('Failed to remove key.');
    } finally {
      setRemoving(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-950 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-semibold text-white mb-1">Settings</h1>
        <p className="text-sm text-slate-400 mb-8">Connect your CMMS to populate TrueSignal with your real equipment data.</p>

        {/* Team section — owner/admin only */}
        {isOwnerOrAdmin && user && (
          <TeamSection currentUserId={user.id} currentUserRole={role} />
        )}

        {/* MaintainX card */}
        <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">MaintainX</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Pull work orders and assets from MaintainX into TrueSignal automatically.
              </p>
            </div>
            {connected === null ? (
              <span className="text-xs text-slate-500 animate-pulse">Checking…</span>
            ) : connected ? (
              <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <span className="h-2 w-2 rounded-full bg-slate-600" />
                Not connected
              </span>
            )}
          </div>

          {connected ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-300">
                Your MaintainX API key is stored securely. TrueSignal syncs your work orders and assets daily.
              </p>
              <div className="flex items-center gap-4">
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {syncing ? 'Syncing…' : 'Sync Now'}
                </button>
                <button
                  onClick={handleRemove}
                  disabled={removing}
                  className="text-sm text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                >
                  {removing ? 'Removing…' : 'Disconnect MaintainX'}
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  API Key
                  <span className="ml-2 text-slate-600">— MaintainX → Settings → Integrations → API</span>
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  placeholder="Paste your MaintainX API key"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  autoComplete="off"
                />
              </div>
              <p className="text-xs text-slate-500">
                Your key is encrypted with AES-256 before storage and never returned to the browser.
              </p>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Connect MaintainX'}
              </button>
            </form>
          )}

          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          {success && <p className="mt-3 text-sm text-emerald-400">{success}</p>}
        </div>

        {/* Future integrations placeholder */}
        <div className="mt-4 bg-slate-900/50 border border-slate-700/30 rounded-xl p-6 opacity-50">
          <h2 className="text-base font-semibold text-slate-400">More integrations coming soon</h2>
          <p className="text-xs text-slate-500 mt-1">Limble, UpKeep, Fiix</p>
        </div>
      </div>
    </div>
  );
}
