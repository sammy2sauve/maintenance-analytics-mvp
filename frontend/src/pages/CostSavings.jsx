import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import EmptyState from '../components/EmptyState';
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';

const STATUS_CONFIG = [
  { key: 'pending',     label: 'Pending',     color: '#fbbf24' },
  { key: 'accepted',    label: 'Accepted',     color: '#6366f1' },
  { key: 'implemented', label: 'Implemented',  color: '#34d399' },
];

function StatusRing({ label, count, total, color }) {
  const pct  = total > 0 ? count / total : 0;
  const r    = 54, cx = 72, cy = 72;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;
  const glowId = `glow-cs-${label}`;

  return (
    <div className="flex flex-col items-center flex-1 min-w-0">
      <svg viewBox="0 0 144 144" className="w-full" style={{ maxWidth: 140 }}>
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="10" />
        {count > 0 && (
          <circle
            cx={cx} cy={cy} r={r}
            fill="none" stroke={color} strokeWidth="10"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform={`rotate(-90 ${cx} ${cy})`}
            filter={`url(#${glowId})`}
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        )}
        <text x={cx} y={cy - 8} textAnchor="middle" dominantBaseline="middle"
          fill="white" fontSize="30" fontWeight="700" fontFamily="sans-serif">
          {count}
        </text>
        <text x={cx} y={cy + 20} textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize="11" fontWeight="500" fontFamily="sans-serif" opacity="0.9">
          {(pct * 100).toFixed(0)}% of total
        </text>
      </svg>
      <p className="text-xs font-bold tracking-wide mt-1" style={{ color }}>{label}</p>
    </div>
  );
}

function WaterfallTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
      <p className="font-semibold text-white mb-1">{d.assetId}</p>
      <div className="space-y-0.5">
        <p className="text-slate-300">
          Est. annual savings: <span className="text-emerald-400 font-semibold">${Math.round(d.savings).toLocaleString()}</span>
        </p>
        <p className="text-slate-300">
          Cumulative if all above applied: <span className="text-emerald-300 font-semibold">${Math.round(d.cumulative).toLocaleString()}/yr</span>
        </p>
        <p className="text-slate-400 mt-1">
          Change PM from every {d.currentFreq} days → every {d.suggestedFreq} days
        </p>
      </div>
    </div>
  );
}

export default function CostSavings() {
  const { hasApiKey, locationId, syncVersion } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [pmData, setPmData]   = useState([]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const locParam = locationId ? { location_id: locationId } : {};
      const res = await getPredictions.pmOptimization({ limit: 1000, ...locParam });
      setPmData(res.data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Cost Savings is a current-state view — no date filter
  useEffect(() => { if (hasApiKey) load(); }, [hasApiKey, syncVersion]);

  if (!hasApiKey) return <EmptyState />;

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-slate-300 text-xl animate-pulse">Loading...</div>
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-red-400 text-center">
        <AlertCircle className="w-12 h-12 mx-auto mb-4" />
        <p>Error: {error}</p>
        <button onClick={load} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">Retry</button>
      </div>
    </div>
  );

  const total        = pmData.length;
  const totalSavings = pmData.reduce((sum, p) => sum + (p.estimated_cost_savings || 0), 0);

  // Status ring counts
  const statusCounts = STATUS_CONFIG.reduce((acc, s) => {
    acc[s.key] = pmData.filter(p => (p.status || 'pending') === s.key).length;
    return acc;
  }, {});

  // Quick Wins: top 7 by savings
  const quickWins = [...pmData]
    .sort((a, b) => (b.estimated_cost_savings || 0) - (a.estimated_cost_savings || 0))
    .slice(0, 7);

  // Waterfall: cumulative savings sorted by savings DESC
  let running = 0;
  const waterfallData = [...pmData]
    .sort((a, b) => (b.estimated_cost_savings || 0) - (a.estimated_cost_savings || 0))
    .map((pm, i) => {
      running += pm.estimated_cost_savings || 0;
      return {
        n:            i + 1,
        cumulative:   running,
        savings:      pm.estimated_cost_savings || 0,
        assetId:      pm.asset_id,
        currentFreq:  pm.current_pm_frequency_days,
        suggestedFreq: pm.suggested_pm_frequency_days,
      };
    });

  // Milestone lines (show at round numbers below total)
  const milestones = [10000, 25000, 50000, 100000].filter(m => m < totalSavings * 0.95);

  const exportCSV = () => {
    const headers = ['asset_id', 'status', 'current_pm_frequency_days', 'suggested_pm_frequency_days', 'estimated_cost_savings', 'reason'];
    const csv = [
      headers.join(','),
      ...pmData.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const s   = String(val).replace(/"/g, '""');
        return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s}"` : s;
      }).join(','))
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    Object.assign(document.createElement('a'), {
      href: url,
      download: `pm_optimization_${new Date().toISOString().split('T')[0]}.csv`,
    }).click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full px-4 py-3">

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">
          Cost Savings
          <span className="text-slate-500 font-normal ml-2">
            ({total} PM opportunities · <span className="text-emerald-400">${Math.round(totalSavings).toLocaleString()}</span> potential/yr)
          </span>
        </h2>
        <button onClick={exportCSV}
          className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded">
          Export CSV
        </button>
      </div>

      <div className="flex-1 min-h-0 flex flex-col gap-3">

        {/* TOP ROW: Status rings + Quick Wins */}
        <div className="flex-[3] min-h-0 flex gap-3">

          {/* PM Status Rings — main panel */}
          <div className="flex-1 min-w-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 flex flex-col">
            <div className="mb-2 flex-shrink-0">
              <h3 className="text-sm font-semibold text-white">PM Suggestion Status</h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Accepted/Implemented status synced from CMMS</p>
            </div>
            <div className="flex-1 flex items-center justify-around gap-2 min-h-0">
              {STATUS_CONFIG.map(s => (
                <StatusRing key={s.key} label={s.label} count={statusCounts[s.key]} total={total} color={s.color} />
              ))}
            </div>
            {/* Big dollar number — the hook */}
            <div className="text-center pt-2 mt-2 border-t border-slate-700/30 flex-shrink-0">
              <p className="text-2xl font-bold text-emerald-400">${Math.round(totalSavings).toLocaleString()}</p>
              <p className="text-[10px] text-slate-500">est. annual savings if all suggestions applied consistently</p>
            </div>
          </div>

          {/* Top Suggestions — slightly wider so all explanation text sits on one row per item */}
          <div className="w-96 flex-shrink-0 bg-slate-900/80 border border-emerald-500/20 rounded-2xl p-3 flex flex-col">
            <div className="flex-shrink-0 mb-2">
              <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">Top Suggestions</h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Highest-value PMs pending review</p>
            </div>
            <div className="flex-1 flex flex-col justify-around">
              {quickWins.length === 0 ? (
                <p className="text-slate-600 text-xs">No opportunities</p>
              ) : quickWins.map((pm, i) => (
                <div key={i} className="flex items-center gap-2 py-1.5 border-b border-slate-800/60 last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                  <span className="text-[11px] font-semibold text-white flex-shrink-0">{pm.asset_id}</span>
                  <span className="text-[10px] text-slate-600 flex-shrink-0">·</span>
                  <span className="text-[10px] text-slate-300 flex-shrink-0 whitespace-nowrap">
                    every {pm.suggested_pm_frequency_days}d <span className="text-slate-500">(was {pm.current_pm_frequency_days}d)</span>
                  </span>
                  <span className="text-[10px] text-emerald-400 font-medium whitespace-nowrap ml-auto flex-shrink-0">
                    Est. ${Math.round(pm.estimated_cost_savings || 0).toLocaleString()}/yr if applied
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: Savings Waterfall */}
        <div className="flex-[2] min-h-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 flex flex-col">
          <div className="mb-2 flex-shrink-0">
            <h3 className="text-sm font-semibold text-white">Cumulative Savings Waterfall</h3>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Sorted by highest estimated savings — shows total annual savings unlocked as each PM suggestion is consistently applied
            </p>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={waterfallData} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <defs>
                  <linearGradient id="savingsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#34d399" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="n"
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  label={{ value: 'PMs Implemented →', position: 'insideBottomRight', offset: -4, fill: '#475569', fontSize: 9 }}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
                  width={40}
                />
                <Tooltip content={<WaterfallTooltip />} cursor={{ stroke: '#475569', strokeDasharray: '3 3' }} />
                {milestones.map(m => (
                  <ReferenceLine key={m} y={m} stroke="#334155" strokeDasharray="4 4" strokeWidth={1}
                    label={{ value: `$${(m / 1000).toFixed(0)}k`, fill: '#475569', fontSize: 9, position: 'insideTopRight' }}
                  />
                ))}
                <Area
                  type="monotone" dataKey="cumulative"
                  stroke="#34d399" strokeWidth={2}
                  fill="url(#savingsGrad)"
                  dot={false}
                  activeDot={{ r: 4, fill: '#34d399', stroke: '#0f172a', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
