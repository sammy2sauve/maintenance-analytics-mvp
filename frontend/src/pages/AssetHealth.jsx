import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle } from 'lucide-react';

const ASSET_TYPE_MAP = {
  PUMP: 'Pump',
  COMP: 'Compressor',
  FAN: 'Fan',
  MOTOR: 'Motor',
  VALVE: 'Valve',
  CONV: 'Conveyor',
  HEAT: 'Heat Exchanger',
  COOL: 'Cooler',
  BOIL: 'Boiler',
  TURB: 'Turbine',
  GEN: 'Generator',
  FILT: 'Filter',
};

function getAssetType(assetId) {
  if (!assetId) return 'Asset';
  const prefix = assetId.split(/[-_\d]/)[0].toUpperCase();
  return ASSET_TYPE_MAP[prefix] || prefix || 'Asset';
}

const COLUMNS = [
  {
    key: 'healthy',
    label: 'Healthy',
    levels: ['LOW', 'MEDIUM'],
    headerColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    bgColor: 'bg-emerald-500/5',
    countBg: 'bg-emerald-500/20 text-emerald-300',
    cardBorder: { LOW: 'border-l-emerald-500', MEDIUM: 'border-l-yellow-500' },
    cardDot: { LOW: 'bg-emerald-400', MEDIUM: 'bg-yellow-400' },
  },
  {
    key: 'high',
    label: 'High Risk',
    levels: ['HIGH'],
    headerColor: 'text-orange-400',
    borderColor: 'border-orange-500/30',
    bgColor: 'bg-orange-500/5',
    countBg: 'bg-orange-500/20 text-orange-300',
    cardBorder: { HIGH: 'border-l-orange-500' },
    cardDot: { HIGH: 'bg-orange-400' },
  },
  {
    key: 'critical',
    label: 'Critical',
    levels: ['CRITICAL'],
    headerColor: 'text-red-400',
    borderColor: 'border-red-500/30',
    bgColor: 'bg-red-500/5',
    countBg: 'bg-red-500/20 text-red-300',
    cardBorder: { CRITICAL: 'border-l-red-500' },
    cardDot: { CRITICAL: 'bg-red-400' },
  },
];

function ProbBar({ value }) {
  const pct = value != null ? Math.round(value * 100) : null;
  if (pct === null) return <span className="text-slate-500 text-[10px]">—</span>;
  const color = pct >= 80 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-400' : pct >= 30 ? 'bg-yellow-400' : 'bg-emerald-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-slate-300 w-7 text-right">{pct}%</span>
    </div>
  );
}

function AssetCard({ asset, col }) {
  const borderClass = col.cardBorder[asset.risk_level] || 'border-l-slate-500';
  const dotClass = col.cardDot[asset.risk_level] || 'bg-slate-400';
  const type = getAssetType(asset.asset_id);

  return (
    <div className={`bg-slate-800/60 border border-slate-700/50 border-l-2 ${borderClass} rounded-lg p-3 hover:bg-slate-800/90 transition-colors`}>
      <div className="flex items-start justify-between mb-1.5">
        <div>
          <p className="text-xs font-semibold text-white leading-tight">{asset.asset_id}</p>
          <p className="text-[10px] text-slate-400 mt-0.5">{type}</p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <div className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
          {asset.days_to_predicted_failure != null && (
            <span className="text-[10px] text-slate-400">{asset.days_to_predicted_failure}d</span>
          )}
        </div>
      </div>
      <ProbBar value={asset.failure_probability} />
      {asset.recommendation && (
        <p className="text-[10px] text-slate-400 mt-1.5 leading-tight line-clamp-2">
          {asset.recommendation}
        </p>
      )}
    </div>
  );
}

function KanbanColumn({ col, assets }) {
  return (
    <div className={`flex flex-col border ${col.borderColor} ${col.bgColor} rounded-2xl overflow-hidden`}>
      {/* Column header */}
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between flex-shrink-0">
        <span className={`text-sm font-semibold ${col.headerColor}`}>{col.label}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${col.countBg}`}>
          {assets.length}
        </span>
      </div>
      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {assets.length === 0 ? (
          <p className="text-center text-slate-600 text-xs py-8">No assets</p>
        ) : (
          assets.map((asset, idx) => (
            <AssetCard key={asset.asset_id ?? idx} asset={asset} col={col} />
          ))
        )}
      </div>
    </div>
  );
}

export default function AssetHealth({ dateRange }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    load();
  }, [dateRange]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = { limit: 1000, ...(dateRange ? { days: dateRange } : {}) };
      const res = await getPredictions.failures(params);
      setPredictions(res.data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-300 text-xl animate-pulse">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-400 text-center">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <p>Error: {error}</p>
          <button onClick={load} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">Retry</button>
        </div>
      </div>
    );
  }

  const filtered = searchQuery
    ? predictions.filter(p => p.asset_id?.toLowerCase().includes(searchQuery.toLowerCase()))
    : predictions;

  const columnAssets = COLUMNS.map(col => ({
    col,
    assets: filtered.filter(p => col.levels.includes(p.risk_level)),
  }));

  const exportCSV = () => {
    const headers = ['asset_id', 'risk_level', 'failure_probability', 'recommendation', 'days_to_predicted_failure', 'prediction_date'];
    const csvContent = [
      headers.join(','),
      ...filtered.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const str = String(val).replace(/"/g, '""');
        return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str}"` : str;
      }).join(','))
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `asset_health_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col px-4 py-4" style={{ height: 'calc(100vh - 96px)' }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">
          Asset Health Board
          <span className="text-slate-500 font-normal ml-2">({filtered.length} assets)</span>
        </h2>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search asset..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-44"
          />
          <button
            onClick={exportCSV}
            className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Kanban columns — fill remaining height */}
      <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
        {columnAssets.map(({ col, assets }) => (
          <KanbanColumn key={col.key} col={col} assets={assets} />
        ))}
      </div>
    </div>
  );
}
