import { useState, useEffect } from 'react';
import { X, Bell, CheckCircle } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const THRESHOLD_PRESETS = {
  overview: [
    { id: 'critical_count',      label: 'Critical assets reach',            unit: 'assets', defaultVal: 3,     type: 'gte' },
    { id: 'high_count',          label: 'High-risk assets exceed',          unit: 'assets', defaultVal: 5,     type: 'gte' },
    { id: 'savings_opportunity', label: 'Total savings opportunity exceeds', unit: '$',      defaultVal: 10000, type: 'gte' },
  ],
  asset_health: [
    { id: 'any_critical', label: 'Any asset becomes CRITICAL', unit: null,   defaultVal: null, type: 'event' },
    { id: 'risk_score',   label: 'Any asset risk score exceeds', unit: '',   defaultVal: 0.7,  type: 'gte' },
    { id: 'no_wo_days',   label: 'Asset has no WO for more than', unit: 'days', defaultVal: 90, type: 'gte' },
  ],
};

const CHANNELS   = ['Email', 'In-app'];
const FREQUENCIES = ['Immediately', 'Daily digest', 'Weekly digest'];

export default function NotifyMeDrawer({ open, onClose, page = 'overview' }) {
  const { locationId } = useAuth();
  const presets = THRESHOLD_PRESETS[page] || THRESHOLD_PRESETS.overview;

  const [rules, setRules] = useState(
    presets.map(p => ({ ...p, enabled: false, value: p.defaultVal, channel: 'Email', frequency: 'Immediately' }))
  );
  const [loading, setLoading] = useState(false);
  const [saving,  setSaving]  = useState(false);
  const [saved,   setSaved]   = useState(false);
  const [error,   setError]   = useState('');

  // Load existing rules when drawer opens
  useEffect(() => {
    if (!open || !locationId) return;
    setLoading(true);
    api.get('/alerts/rules', { params: { location_id: locationId } })
      .then(res => {
        const saved = res.data.rules || [];
        setRules(presets.map(p => {
          const match = saved.find(r => r.rule_key === p.id);
          return match
            ? { ...p, enabled: match.enabled, value: match.threshold ?? p.defaultVal, channel: match.channel, frequency: match.frequency }
            : { ...p, enabled: false, value: p.defaultVal, channel: 'Email', frequency: 'Immediately' };
        }));
      })
      .catch(() => { /* use defaults on error */ })
      .finally(() => setLoading(false));
  }, [open, locationId]);

  const toggle    = (id)           => setRules(prev => prev.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
  const setValue  = (id, value)    => setRules(prev => prev.map(r => r.id === id ? { ...r, value } : r));
  const setChannel   = (id, ch)   => setRules(prev => prev.map(r => r.id === id ? { ...r, channel: ch } : r));
  const setFrequency = (id, freq) => setRules(prev => prev.map(r => r.id === id ? { ...r, frequency: freq } : r));

  const handleSave = async () => {
    setSaving(true); setError('');
    try {
      await api.post('/alerts/rules', {
        location_id: locationId,
        rules: rules.map(r => ({
          rule_key:  r.id,
          threshold: r.type === 'event' ? null : Number(r.value),
          channel:   r.channel,
          frequency: r.frequency,
          enabled:   r.enabled,
        })),
      });
      setSaved(true);
      setTimeout(() => { setSaved(false); onClose(); }, 1200);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save alerts');
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-96 bg-slate-900 border-l border-slate-700 z-50 flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div className="flex items-center gap-2.5">
            <Bell className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-semibold text-white">Notify Me</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          <p className="text-xs text-slate-400">
            Alerts are evaluated after each sync and sent to your account email.
          </p>

          {loading ? (
            <p className="text-xs text-slate-500 animate-pulse">Loading your saved rules…</p>
          ) : (
            rules.map(rule => (
              <div
                key={rule.id}
                className={`rounded-xl border p-4 transition-colors ${
                  rule.enabled ? 'bg-amber-500/5 border-amber-500/20' : 'bg-slate-800/50 border-slate-700/50'
                }`}
              >
                {/* Toggle row */}
                <div className="flex items-center gap-3 mb-3">
                  <button
                    onClick={() => toggle(rule.id)}
                    className={`relative flex-shrink-0 w-9 h-5 rounded-full transition-colors ${rule.enabled ? 'bg-amber-500' : 'bg-slate-600'}`}
                  >
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${rule.enabled ? 'translate-x-4' : ''}`} />
                  </button>
                  <span className={`text-sm font-medium transition-colors ${rule.enabled ? 'text-white' : 'text-slate-400'}`}>
                    {rule.label}
                    {rule.unit === '$' && rule.value !== null && rule.enabled && (
                      <span className="text-amber-400 ml-1">${Number(rule.value).toLocaleString()}</span>
                    )}
                    {rule.unit && rule.unit !== '$' && rule.value !== null && rule.enabled && (
                      <span className="text-amber-400 ml-1">{rule.value} {rule.unit}</span>
                    )}
                  </span>
                </div>

                {rule.enabled && (
                  <div className="space-y-2.5 pl-12">
                    {rule.type !== 'event' && rule.value !== null && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 w-16">Threshold</span>
                        <input
                          type="number"
                          value={rule.value}
                          onChange={e => setValue(rule.id, e.target.value)}
                          className="w-24 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-amber-500"
                        />
                        {rule.unit && <span className="text-xs text-slate-400">{rule.unit}</span>}
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 w-16">Via</span>
                      <div className="flex gap-1.5">
                        {CHANNELS.map(ch => (
                          <button
                            key={ch}
                            onClick={() => setChannel(rule.id, ch)}
                            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                              rule.channel === ch ? 'bg-amber-500 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'
                            }`}
                          >{ch}</button>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 w-16">When</span>
                      <select
                        value={rule.frequency}
                        onChange={e => setFrequency(rule.id, e.target.value)}
                        className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-amber-500"
                      >
                        {FREQUENCIES.map(f => <option key={f}>{f}</option>)}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-700">
          {error && <p className="text-xs text-red-400 mb-2">{error}</p>}
          <button
            onClick={handleSave}
            disabled={saving || saved}
            className={`w-full flex items-center justify-center gap-2 text-sm font-medium py-2.5 rounded-lg transition-all ${
              saved    ? 'bg-emerald-600 text-white' :
              saving   ? 'bg-slate-700 text-slate-400' :
              rules.some(r => r.enabled) ? 'bg-amber-500 hover:bg-amber-600 text-white' :
              'bg-slate-700 text-slate-500'
            }`}
          >
            {saved   ? <><CheckCircle className="w-4 h-4" /> Saved!</> :
             saving  ? 'Saving…' :
             <><Bell className="w-4 h-4" /> Save Alerts</>}
          </button>
          <p className="text-[11px] text-slate-500 text-center mt-2">
            Alerts fire to your account email after each sync.
          </p>
        </div>
      </div>
    </>
  );
}
