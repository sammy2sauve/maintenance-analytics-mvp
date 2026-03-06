import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle } from 'lucide-react';
import {
  Treemap, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

const RISK_COLORS = { LOW: '#34d399', MEDIUM: '#fbbf24', HIGH: '#fb923c', CRITICAL: '#f87171' };
const RISK_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const RISK_PRIORITY = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

const ASSET_TYPE_MAP = {
  PUMP: 'Pump', COMP: 'Compressor', FAN: 'Fan', MOTOR: 'Motor',
  VALVE: 'Valve', CONV: 'Conveyor', HEAT: 'Heat Exchanger',
  COOL: 'Cooler', BOIL: 'Boiler', TURB: 'Turbine',
  GEN: 'Generator', FILT: 'Filter',
};

// Rename x/y → days/prob to avoid conflicts with recharts SVG coords in Treemap cell props
const DAY_BUCKETS = [
  { key: 'd90plus', label: '90+ days',   color: '#34d399' },
  { key: 'd60_90', label: '60–90 days',  color: '#fbbf24' },
  { key: 'd30_60', label: '30–60 days',  color: '#fb923c' },
  { key: 'd0_30',  label: '0–30 days',   color: '#f87171' },
];

function getAssetType(id) {
  if (!id) return 'Asset';
  const p = id.split(/[-_\d]/)[0].toUpperCase();
  return ASSET_TYPE_MAP[p] || p || 'Asset';
}

function TimelineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
      <p className="font-semibold text-white mb-2">{label}</p>
      {[...payload].reverse().map((p, i) => p.value > 0 && (
        <div key={i} className="flex items-center gap-2 mb-0.5">
          <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: p.fill }} />
          <span className="text-slate-300">{p.name}: <span className="text-white font-semibold">{p.value}</span> assets</span>
        </div>
      ))}
    </div>
  );
}

export default function AssetHealth({ dateRange }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [search, setSearch] = useState('');
  const [tmHover, setTmHover] = useState(null);
  const [tmPos, setTmPos] = useState({ x: 0, y: 0 });

  useEffect(() => { load(); }, [dateRange]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getPredictions.failures({ limit: 1000, ...(dateRange ? { days: dateRange } : {}) });
      setPredictions(res.data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-300 text-xl animate-pulse">Loading...</div>
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center h-64">
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

  // Use `days` and `prob` instead of `x`/`y` to avoid collision with recharts SVG coords
  const plotReady = filtered
    .filter(p => p.failure_probability != null)
    .map(p => ({
      days: p.days_to_predicted_failure,
      prob: Math.round(p.failure_probability * 100),
      assetId: p.asset_id,
      type: getAssetType(p.asset_id),
      riskLevel: p.risk_level,
      recommendation: p.recommendation,
    }));

  const withDays = plotReady.filter(p => p.days != null);

  // Treemap: size = failure probability, color = risk level
  const treemapData = plotReady.map(p => ({
    name: p.assetId,
    size: Math.max(p.prob, 4),
    ...p,
  }));

  // Act Now: top 7 CRITICAL/HIGH sorted by urgency
  const actNow = plotReady
    .filter(p => p.riskLevel === 'CRITICAL' || p.riskLevel === 'HIGH')
    .sort((a, b) => {
      const pd = RISK_PRIORITY[a.riskLevel] - RISK_PRIORITY[b.riskLevel];
      return pd !== 0 ? pd : (a.days ?? 999) - (b.days ?? 999);
    })
    .slice(0, 7);

  // Timeline: stacked bar by equipment type × days bucket
  const assetTypes = [...new Set(withDays.map(p => p.type))].sort();
  const timelineData = assetTypes.map(type => {
    const assets = withDays.filter(p => p.type === type);
    return {
      type,
      'd90plus': assets.filter(p => p.days > 90).length,
      'd60_90':  assets.filter(p => p.days > 60 && p.days <= 90).length,
      'd30_60':  assets.filter(p => p.days > 30 && p.days <= 60).length,
      'd0_30':   assets.filter(p => p.days <= 30).length,
    };
  });

  // Treemap cell — defined inside component to close over setTmHover / setTmPos
  const renderTreemapCell = (props) => {
    // recharts passes SVG x/y/width/height + all data fields
    const { x, y, width, height, name, riskLevel } = props;
    const color = RISK_COLORS[riskLevel] || '#94a3b8';
    const showLabel = width > 38 && height > 22;
    const fontSize = Math.max(7, Math.min(11, width / 7));

    return (
      <g
        onMouseEnter={() => setTmHover({
          name,
          riskLevel,
          type: props.type,
          days: props.days,
          prob: props.prob,
          recommendation: props.recommendation,
        })}
        onMouseLeave={() => setTmHover(null)}
        onMouseMove={e => setTmPos({ x: e.clientX, y: e.clientY })}
        style={{ cursor: 'default' }}
      >
        <rect
          x={x} y={y} width={width} height={height}
          fill={color} fillOpacity={0.78}
          stroke="#0f172a" strokeWidth={1.5}
          rx={2}
        />
        {showLabel && (
          <text
            x={x + width / 2} y={y + height / 2}
            textAnchor="middle" dominantBaseline="middle"
            fill="white" fontSize={fontSize}
            style={{ pointerEvents: 'none', userSelect: 'none', fontWeight: 600 }}
          >
            {name}
          </text>
        )}
      </g>
    );
  };

  const exportCSV = () => {
    const headers = ['asset_id', 'risk_level', 'failure_probability', 'days_to_predicted_failure', 'recommendation'];
    const csv = [
      headers.join(','),
      ...filtered.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const s = String(val).replace(/"/g, '""');
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
          <span className="text-slate-500 font-normal ml-2">({filtered.length} assets)</span>
        </h2>
        <div className="flex items-center gap-3">
          <input
            type="text" placeholder="Search asset..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-36"
          />
          <button onClick={exportCSV} className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded">
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col gap-3">

        {/* TOP ROW: Treemap + Act Now */}
        <div className="flex-[3] min-h-0 flex gap-3">

          {/* Risk Overview Treemap */}
          <div className="flex-1 min-w-0 min-h-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 flex flex-col">
            <div className="flex items-start justify-between mb-2 flex-shrink-0">
              <div>
                <h3 className="text-sm font-semibold text-white">Risk Overview</h3>
                <p className="text-[10px] text-slate-500 mt-0.5">Larger rectangle = higher failure probability · Hover any asset for details</p>
              </div>
              <div className="flex gap-3 flex-shrink-0">
                {RISK_ORDER.map(level => (
                  <div key={level} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-sm" style={{ background: RISK_COLORS[level], opacity: 0.8 }} />
                    <span className="text-[10px] text-slate-400">{level}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex-1 min-h-0 relative" onMouseLeave={() => setTmHover(null)}>
              <ResponsiveContainer width="100%" height="100%">
                <Treemap
                  data={treemapData}
                  dataKey="size"
                  content={renderTreemapCell}
                  isAnimationActive={false}
                />
              </ResponsiveContainer>

              {/* Floating tooltip — fixed position follows cursor */}
              {tmHover && (
                <div
                  className="fixed z-50 pointer-events-none bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs max-w-[210px]"
                  style={{ left: tmPos.x + 14, top: tmPos.y - 10 }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-white">{tmHover.name}</span>
                    <span className="text-[10px] ml-2 font-semibold" style={{ color: RISK_COLORS[tmHover.riskLevel] }}>
                      {tmHover.riskLevel}
                    </span>
                  </div>
                  <p className="text-slate-400 text-[10px] mb-1">{tmHover.type}</p>
                  <div className="flex gap-2 text-[10px] text-slate-300">
                    <span>{tmHover.prob}% probability</span>
                    {tmHover.days != null && <><span>·</span><span>{tmHover.days}d left</span></>}
                  </div>
                  {tmHover.recommendation && (
                    <p className="text-slate-400 text-[10px] mt-1.5 leading-tight border-t border-slate-700 pt-1.5">
                      {tmHover.recommendation}
                    </p>
                  )}
                </div>
              )}
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
                    {a.days != null && <span className="text-[10px] text-slate-400">{a.days}d</span>}
                    <span className="text-[10px] text-slate-500">{a.prob}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: Failure Timeline */}
        <div className="flex-[2] min-h-0 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 flex flex-col">
          <div className="flex items-start justify-between mb-2 flex-shrink-0">
            <div>
              <h3 className="text-sm font-semibold text-white">Failure Timeline by Equipment Type</h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Stacked by urgency — red = failing within 30 days</p>
            </div>
            {/* Legend: urgent first */}
            <div className="flex gap-3 flex-shrink-0">
              {[...DAY_BUCKETS].reverse().map(b => (
                <div key={b.key} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-sm" style={{ background: b.color }} />
                  <span className="text-[10px] text-slate-400">{b.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={timelineData} margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  tickFormatter={v => `${v}`}
                  label={{ value: '← Safe   |   Urgent →', position: 'insideBottomRight', offset: -4, fill: '#475569', fontSize: 9 }}
                />
                <YAxis
                  type="category" dataKey="type"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  width={72}
                />
                <Tooltip content={<TimelineTooltip />} cursor={{ fill: '#1e293b66' }} />
                {/* Stack order: safe (left) → urgent (right) */}
                {DAY_BUCKETS.map(b => (
                  <Bar key={b.key} dataKey={b.key} stackId="a" fill={b.color} name={b.label} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
