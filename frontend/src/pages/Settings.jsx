import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const API = 'http://localhost:8000';

function authHeaders() {
  const token = localStorage.getItem('ts_token');
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

export default function Settings() {
  const { refreshLocation } = useAuth();
  const [connected, setConnected] = useState(null); // null = loading
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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
