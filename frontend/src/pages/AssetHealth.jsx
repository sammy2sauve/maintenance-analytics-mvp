import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import GatedView from '../components/GatedView';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const RISK_COLORS  = { LOW: '#34d399', MEDIUM: '#fbbf24', HIGH: '#fb923c', CRITICAL: '#f87171' };
const RISK_ORDER   = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const RISK_PRIORITY = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

const URGENCY_BUCKETS = [
  { label: '0–7d',   min: 0,   max: 7,   color: '#f87171' },
  { label: '8–14d',  min: 8,   max: 14,  color: '#fb923c' },
  { label: '15–30d', min: 15,  max: 30,  color: '#fbbf24' },
  { label: '31–60d', min: 31,  max: 60,  color: '#a3e635' },
  { label: '61–90d', min: 61,  max: 90,  color: '#34d399' },
  { label: '90+d',   min: 91,  max: Infinity, color: '#34d399' },
];

// Draws a single circular progress ring + centered stat
function RiskRing({ level, count, total }) {
  const pct   = total > 0 ? count / total : 0;
  const color = RISK_COLORS[level];
  const r     = 54;
  const cx    = 72;
  const cy    = 72;
  const circ  = 2 * Math.PI * r;
  const dash  = pct * circ;

  const glowId = `glow-${level}`;

  return (
    <div className="flex flex-col items-center flex-1 min-w-0">
      <svg viewBox="0 0 144 144" className="w-full" style={{ maxWidth: 150 }}>
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="10" />

        {/* Progress arc */}
        {count > 0 && (
          <circle
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform={`rotate(-90 ${cx} ${cy})`}
            filter={`url(#${glowId})`}
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        )}

        {/* Count */}
        <text x={cx} y={cy - 8} textAnchor="middle" dominantBaseline="middle"
          fill="white" fontSize="30" fontWeight="700" fontFamily="sans-serif">
          {count}
        </text>

        {/* Pct */}
        <text x={cx} y={cy + 20} textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize="12" fontWeight="500" fontFamily="sans-serif" opacity="0.9">
          {(pct * 100).toFixed(0)}% of fleet
        </text>
      </svg>

      <p className="text-xs font-bold tracking-wide mt-1" style={{ color }}>{level}</p>
    </div>
  );
}

function HistogramTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
      <p className="font-semibold text-white mb-1">{label}</p>
      <p className="text-slate-300">{payload[0].value} assets predicted to fail</p>
    </div>
  );
}

function AssetHealthSkeleton() {
  const rings = [
    { color: '#f87171', label: 'CRITICAL', count: 2 },
    { color: '#fb923c', label: 'HIGH',     count: 7 },
    { color: '#fbbf24', label: 'MEDIUM',   count: 9 },
    { color: '#34d399', label: 'LOW',      count: 11 },
  ];
  return (
    <div className="w-full h-full p-4 space-y-4 overflow-hidden">
      {/* Risk rings */}
      <div className="grid grid-cols-4 gap-4">
        {rings.map(({ color, label, count }) => (
          <div key={label} className="bg-slate-800 rounded-xl border border-slate-700/50 p-5 flex flex-col items-center gap-3">
            <div className="relative w-20 h-20">
              <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                <circle cx="40" cy="40" r="32" fill="none" stroke="#334155" strokeWidth="8" />
                <circle cx="40" cy="40" r="32" fill="none" stroke={color} strokeWidth="8"
                  strokeDasharray={`${count * 8} 201`} strokeLinecap="round" opacity="0.7" />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-lg font-bold" style={{ color }}>{count}</span>
            </div>
            <span className="text-xs font-semibold text-slate-500">{label}</span>
          </div>
        ))}
      </div>
      {/* Two-col layout */}
      <div className="flex gap-4 flex-1">
        <div className="flex-1 bg-slate-800 rounded-xl border border-slate-700/50 p-4 space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-700/30">
              <div className="w-2 h-2 rounded-full bg-slate-600" />
              <div className="flex-1 h-3 bg-slate-700 rounded" />
              <div className="w-12 h-3 bg-slate-700/60 rounded" />
            </div>
          ))}
        </div>
        <div className="w-56 bg-slate-800 rounded-xl border border-slate-700/50 p-4 space-y-3">
          <div className="w-2/3 h-3 bg-slate-700 rounded mb-4" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-slate-700/60 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function AssetHealth({ dateRange }) {
  const { hasApiKey, locationId, syncVersion } = useAuth();
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [search, setSearch]       = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const locParam = locationId ? { location_id: locationId } : {};
      const res = await getPredictions.failures({ limit: 1000, ...locParam });
      const data = res.data || [];

      // Keep only the latest prediction per asset
      const latestByAsset = new Map();
      data.forEach(p => {
        const existing = latestByAsset.get(p.asset_id);
        if (!existing || (p.prediction_date ?? '') > (existing.prediction_date ?? '')) {
          latestByAsset.set(p.asset_id, p);
        }
      });

      setPredictions(Array.from(latestByAsset.values()));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Asset Health is a current-state view — ignore the date range filter.
  // We fetch ALL predictions and deduplicate to the most recent per asset,
  // so the total count is stable and reflects the full monitored fleet.
  useEffect(() => { if (hasApiKey) load(); }, [hasApiKey, syncVersion]);

  if (!hasApiKey) return (
    <GatedView
      title="Asset health"
      description="Connect FaciliWorks to see per-asset risk scores, CRITICAL/HIGH alerts, and your Act Now priority list."
      skeleton={<AssetHealthSkeleton />}
    />
  );

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

  const filtered = search
    ? predictions.filter(p => p.asset_id?.toLowerCase().includes(search.toLowerCase()))
    : predictions;

  const total = filtered.length;

  // Risk level counts
  const riskCounts = RISK_ORDER.reduce((acc, l) => {
    acc[l] = filtered.filter(p => p.risk_level === l).length;
    return acc;
  }, {});

  // Act Now: top 7 CRITICAL/HIGH by urgency
  const actNow = filtered
    .filter(p => (p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH') && p.failure_probability != null)
    .map(p => ({
      assetId: p.asset_id,
      riskLevel: p.risk_level,
      days: p.days_to_predicted_failure,
      prob: Math.round(p.failure_probability * 100),
      recommendation: p.recommendation,
    }))
    .sort((a, b) => {
      const pd = RISK_PRIORITY[a.riskLevel] - RISK_PRIORITY[b.riskLevel];
      return pd !== 0 ? pd : (a.days ?? 999) - (b.days ?? 999);
    })
    .slice(0, 7);

  // Urgency histogram — all assets bucketed by days_to_predicted_failure.
  // Assets with no predicted failure window (LOW/MEDIUM, null) are treated as 90+d (healthy).
  const histData = URGENCY_BUCKETS.map(b => ({
    label: b.label,
    count: filtered.filter(p => {
      const days = (p.days_to_predicted_failure == null || p.days_to_predicted_failure === 0) ? 999 : p.days_to_predicted_failure;
      return days >= b.min && days <= b.max;
    }).length,
    color: b.color,
  }));

  const exportCSV = () => {
    const headers = ['asset_id', 'risk_level', 'failure_probability', 'days_to_predicted_failure', 'recommendation'];
    const csv = [
      headers.join(','),
      ...filtered.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const s   = String(val).replace(/"/g, '""');
        return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s}"` : s;
      }).join(','))
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    Object.assign(document.createElement('a'), {
      href: url,
      download: `asset_health_${new Date().toISOString().split('T')[0]}.csv`,
    }).click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full px-4 py-3">

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">
          Asset Health
          <span className="text-slate-500 font-normal ml-2">({total} assets)</span>
        </h2>
        <div className="flex items-center gap-2">
          <input
            type="text" placeholder="Search asset..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-36"
          />
          <button onClick={exportCSV}
            className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded">
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col gap-3">

        {/* TOP ROW: Risk Rings + Act Now */}
        <div className="flex-[3] min-h-0 flex gap-3">

          {/* 4 Risk Rings */}
          <div className="flex-1 min-w-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 flex flex-col">
            <div className="mb-3 flex-shrink-0">
              <h3 className="text-sm font-semibold text-white">Fleet Risk Breakdown</h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Arc = share of total fleet · {total} assets monitored</p>
            </div>
            <div className="flex-1 flex items-center justify-around gap-2 min-h-0">
              {RISK_ORDER.map(level => (
                <RiskRing key={level} level={level} count={riskCounts[level]} total={total} />
              ))}
            </div>
          </div>

          {/* Act Now */}
          <div className="w-44 flex-shrink-0 bg-slate-900/80 border border-red-500/20 rounded-2xl p-3 flex flex-col">
            <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-2 flex-shrink-0">Act Now</h3>
            <div className="flex-1 overflow-y-auto space-y-2">
              {actNow.length === 0 ? (
                <p className="text-slate-600 text-xs">No urgent assets</p>
              ) : actNow.map((a, i) => (
                <div key={i} className="border-l-2 pl-2" style={{ borderColor: RISK_COLORS[a.riskLevel] }}>
                  <p className="text-xs font-semibold text-white leading-none">{a.assetId}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[10px] font-medium" style={{ color: RISK_COLORS[a.riskLevel] }}>{a.riskLevel}</span>
                    {a.days != null && a.days > 0 && <span className="text-[10px] text-slate-400">{a.days}d</span>}
                    <span className="text-[10px] text-slate-500">{a.prob}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: Urgency Histogram */}
        <div className="flex-[2] min-h-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 flex flex-col">
          <div className="mb-2 flex-shrink-0">
            <h3 className="text-sm font-semibold text-white">Failure Urgency Distribution</h3>
            <p className="text-[10px] text-slate-500 mt-0.5">How many assets are predicted to fail in each window</p>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={histData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: '#334155' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={28}
                />
                <Tooltip content={<HistogramTooltip />} cursor={{ fill: '#1e293b88' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {histData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
