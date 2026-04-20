import { useState, useEffect } from 'react';
import { getPredictions, getSettings } from '../services/api';
import { useAuth } from '../context/AuthContext';
import GatedView from '../components/GatedView';
import { AlertCircle, ChevronRight, Zap } from 'lucide-react';

const STATUS_STYLES = {
  pending:     { bg: 'bg-amber-500/10',  text: 'text-amber-400',  border: 'border-amber-500/20'  },
  accepted:    { bg: 'bg-emerald-500/10',text: 'text-emerald-400',border: 'border-emerald-500/20'},
  rejected:    { bg: 'bg-red-500/10',    text: 'text-red-400',    border: 'border-red-500/20'    },
  implemented: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20' },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.pending;
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border capitalize ${s.bg} ${s.text} ${s.border}`}>
      {status}
    </span>
  );
}

function FreqArrow({ from, to }) {
  const tighter = to < from;
  return (
    <span className="flex items-center gap-1 text-xs font-mono">
      <span className="text-slate-400">{from}d</span>
      <ChevronRight className={`w-3 h-3 ${tighter ? 'text-emerald-400' : 'text-amber-400'}`} />
      <span className={tighter ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>{to}d</span>
    </span>
  );
}

function StatCard({ label, value, color }) {
  const colors = {
    amber:   'text-amber-400',
    emerald: 'text-emerald-400',
    indigo:  'text-indigo-400',
    slate:   'text-slate-400',
  };
  return (
    <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-3xl font-bold ${colors[color]}`}>{value}</p>
    </div>
  );
}

function PMPlannerSkeleton() {
  const statColors = ['#fbbf24', '#34d399', '#6366f1', '#64748b'];
  return (
    <div className="w-full h-full px-4 py-4 space-y-4 overflow-hidden">
      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3">
        {statColors.map((c, i) => (
          <div key={i} className="bg-slate-800 rounded-xl h-20 border border-slate-700/50 p-4">
            <div className="w-1/2 h-2 bg-slate-700 rounded mb-2" />
            <div className="h-7 w-10 rounded" style={{ background: c, opacity: 0.3 }} />
          </div>
        ))}
      </div>
      {/* Filter tabs */}
      <div className="flex gap-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-6 w-16 bg-slate-800 rounded-full border border-slate-700/50" />
        ))}
      </div>
      {/* Two-col layout */}
      <div className="flex gap-4">
        <div className="flex-1 space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-slate-800 rounded-xl border border-slate-700/50 p-4 space-y-2">
              <div className="flex gap-2">
                <div className="w-24 h-3 bg-slate-700 rounded" />
                <div className="w-14 h-3 bg-slate-700/60 rounded" />
              </div>
              <div className="flex gap-2 items-center">
                <div className="w-8 h-3 bg-slate-700 rounded" />
                <div className="w-3 h-3 bg-slate-700 rounded" />
                <div className="w-8 h-3 bg-emerald-500/30 rounded" />
              </div>
              <div className="w-full h-2 bg-slate-700/40 rounded" />
            </div>
          ))}
        </div>
        <div className="w-80 bg-slate-800 rounded-xl border border-slate-700/50 p-5 space-y-4">
          <div className="w-1/2 h-4 bg-slate-700 rounded" />
          <div className="h-20 bg-slate-700/50 rounded-lg" />
          <div className="grid grid-cols-2 gap-2">
            {[...Array(2)].map((_, i) => <div key={i} className="h-12 bg-slate-700/50 rounded-lg" />)}
          </div>
          <div className="space-y-2">
            <div className="w-full h-2 bg-slate-700/40 rounded" />
            <div className="w-4/5 h-2 bg-slate-700/40 rounded" />
            <div className="w-3/5 h-2 bg-slate-700/40 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PMPlanner() {
  const { hasApiKey, locationId } = useAuth();
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState(null); // { woId, error }
  const [statusFilter, setStatusFilter] = useState('all');

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const locParam = locationId ? { location_id: locationId } : {};
      const res = await getPredictions.pmOptimization({ limit: 200, status: undefined, ...locParam });
      setSuggestions(res.data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (hasApiKey) load(); }, [hasApiKey, locationId]);

  if (!hasApiKey) return (
    <GatedView
      title="PM Planner"
      description="Connect FaciliWorks to get AI-generated PM schedule recommendations you can review, accept, and push directly to your CMMS."
      skeleton={<PMPlannerSkeleton />}
    />
  );

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-slate-300 text-xl animate-pulse">Loading…</div>
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-red-400 text-center">
        <AlertCircle className="w-10 h-10 mx-auto mb-3" />
        <p>{error}</p>
        <button onClick={load} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm">Retry</button>
      </div>
    </div>
  );

  const counts = {
    pending:     suggestions.filter(s => s.status === 'pending').length,
    accepted:    suggestions.filter(s => s.status === 'accepted').length,
    implemented: suggestions.filter(s => s.status === 'implemented').length,
    rejected:    suggestions.filter(s => s.status === 'rejected').length,
  };

  const filtered = statusFilter === 'all'
    ? suggestions
    : suggestions.filter(s => s.status === statusFilter);

  const selectedItem = selected != null ? suggestions.find(s => s.id === selected) : null;

  const updateStatus = async (id, status) => {
    setUpdating(true);
    try {
      await getPredictions.updateSuggestionStatus(id, status);
      setSuggestions(prev => prev.map(s => s.id === id ? { ...s, status } : s));
      if (selectedItem?.id === id) setSelected(null);
    } catch {
      // silently fail — user can retry
    } finally {
      setUpdating(false);
    }
  };

  const pushToFaciliWorks = async (id) => {
    setPushing(true);
    setPushResult(null);
    try {
      const res = await getSettings.pushToFaciliWorks(id, locationId);
      const woId = res.data?.wo_id;
      setSuggestions(prev => prev.map(s => s.id === id ? { ...s, status: 'accepted' } : s));
      setPushResult({ woId });
      setTimeout(() => setPushResult(null), 5000);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Push failed';
      setPushResult({ error: msg });
      setTimeout(() => setPushResult(null), 6000);
    } finally {
      setPushing(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col px-4 py-4 overflow-hidden">

      {/* Header + stats */}
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-semibold text-white">PM Planner</h1>
            <p className="text-xs text-slate-500 mt-0.5">Review AI-generated maintenance schedule recommendations</p>
          </div>
          {pushResult?.woId && (
            <span className="text-xs text-emerald-400 font-medium">Created: {pushResult.woId}</span>
          )}
          {pushResult?.error && (
            <span className="text-xs text-red-400">{pushResult.error}</span>
          )}
        </div>

        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Pending review" value={counts.pending}     color="amber"   />
          <StatCard label="Accepted"        value={counts.accepted}    color="emerald" />
          <StatCard label="Implemented"     value={counts.implemented} color="indigo"  />
          <StatCard label="Rejected"        value={counts.rejected}    color="slate"   />
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-3 flex-shrink-0">
        {['all', 'pending', 'accepted', 'rejected', 'implemented'].map(f => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
              statusFilter === f
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            {f === 'all' ? `All (${suggestions.length})` : f}
          </button>
        ))}
      </div>

      {/* Two-panel layout */}
      <div className="flex-1 min-h-0 flex gap-4">

        {/* Left: suggestion list */}
        <div className="flex-1 min-w-0 overflow-y-auto space-y-2 pr-1">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-slate-500 text-sm">No suggestions in this category</div>
          ) : filtered.map(s => (
            <div
              key={s.id}
              onClick={() => setSelected(s.id === selected ? null : s.id)}
              className={`bg-slate-900/80 border rounded-xl p-4 cursor-pointer transition-all duration-150 ${
                selected === s.id
                  ? 'border-indigo-500/50 bg-indigo-950/30'
                  : 'border-slate-700/50 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-sm font-semibold text-white truncate">{s.asset_id}</span>
                    <StatusBadge status={s.status} />
                  </div>
                  <FreqArrow from={s.current_pm_frequency_days} to={s.suggested_pm_frequency_days} />
                  <p className="text-[11px] text-slate-500 mt-1.5 leading-snug line-clamp-2">{s.reason}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  {s.confidence_score != null && (
                    <p className="text-xs text-slate-400">{Math.round(s.confidence_score * 100)}% conf</p>
                  )}
                  {s.estimated_risk_change != null && (
                    <p className="text-[11px] text-emerald-400 mt-0.5">
                      {s.estimated_risk_change > 0 ? '+' : ''}{(s.estimated_risk_change * 100).toFixed(0)}% risk
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Right: detail panel */}
        <div className="w-80 flex-shrink-0">
          {!selectedItem ? (
            <div className="h-full bg-slate-900/50 border border-slate-700/30 rounded-xl flex items-center justify-center">
              <p className="text-xs text-slate-600 text-center px-6">Select a suggestion to review details and take action</p>
            </div>
          ) : (
            <div className="h-full bg-slate-900/80 border border-slate-700/50 rounded-xl p-5 overflow-y-auto flex flex-col gap-4">

              {/* Asset + status */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="text-base font-semibold text-white">{selectedItem.asset_id}</h2>
                  <StatusBadge status={selectedItem.status} />
                </div>
                <p className="text-xs text-slate-500">
                  Suggestion date: {selectedItem.suggestion_date
                    ? new Date(selectedItem.suggestion_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                    : '—'}
                </p>
              </div>

              {/* Frequency change */}
              <div className="bg-slate-800/60 rounded-lg p-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">PM Frequency</p>
                <div className="flex items-center justify-between">
                  <div className="text-center">
                    <p className="text-xl font-bold text-slate-300">{selectedItem.current_pm_frequency_days}d</p>
                    <p className="text-[10px] text-slate-500">Current</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-indigo-400" />
                  <div className="text-center">
                    <p className="text-xl font-bold text-emerald-400">{selectedItem.suggested_pm_frequency_days}d</p>
                    <p className="text-[10px] text-slate-500">Suggested</p>
                  </div>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-800/40 rounded-lg p-2.5 text-center">
                  <p className="text-xs font-semibold text-white">
                    {selectedItem.confidence_score != null ? `${Math.round(selectedItem.confidence_score * 100)}%` : '—'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Confidence</p>
                </div>
                <div className="bg-slate-800/40 rounded-lg p-2.5 text-center">
                  <p className="text-xs font-semibold text-emerald-400">
                    {selectedItem.estimated_risk_change != null
                      ? `${(selectedItem.estimated_risk_change * 100).toFixed(0)}%`
                      : '—'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Risk change</p>
                </div>
                {selectedItem.reactive_work_after_pm_count != null && (
                  <div className="bg-slate-800/40 rounded-lg p-2.5 text-center col-span-2">
                    <p className="text-xs font-semibold text-amber-400">{selectedItem.reactive_work_after_pm_count}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Reactive WOs after last PM</p>
                  </div>
                )}
              </div>

              {/* Reason */}
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1.5">Reasoning</p>
                <p className="text-xs text-slate-300 leading-relaxed">{selectedItem.reason}</p>
              </div>

              {/* Actions */}
              <div className="mt-auto space-y-2 pt-2 border-t border-slate-700/40">
                {selectedItem.status !== 'accepted' && selectedItem.status !== 'implemented' && (
                  <button
                    onClick={() => updateStatus(selectedItem.id, 'accepted')}
                    disabled={updating}
                    className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                  >
                    {updating ? 'Saving…' : 'Accept'}
                  </button>
                )}
                {selectedItem.status !== 'rejected' && selectedItem.status !== 'implemented' && (
                  <button
                    onClick={() => updateStatus(selectedItem.id, 'rejected')}
                    disabled={updating}
                    className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                  >
                    Reject
                  </button>
                )}
                {selectedItem.status === 'rejected' || selectedItem.status === 'accepted' ? (
                  <button
                    onClick={() => updateStatus(selectedItem.id, 'pending')}
                    disabled={updating}
                    className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-500 text-xs rounded-lg transition-colors disabled:opacity-50"
                  >
                    Reset to pending
                  </button>
                ) : null}
                {hasApiKey && selectedItem.status !== 'implemented' && (
                  <button
                    onClick={() => pushToFaciliWorks(selectedItem.id)}
                    disabled={pushing}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Zap className="w-3 h-3" />
                    {pushing ? 'Sending to FaciliWorks…' : 'Generate in FaciliWorks'}
                  </button>
                )}
                {!hasApiKey && (
                  <button
                    disabled
                    title="Connect FaciliWorks in Settings to enable"
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-800/50 border border-slate-700/30 text-slate-600 text-xs rounded-lg cursor-not-allowed"
                  >
                    <Zap className="w-3 h-3" />
                    Generate in FaciliWorks
                  </button>
                )}
              </div>

            </div>
          )}
        </div>

      </div>
    </div>
  );
}
