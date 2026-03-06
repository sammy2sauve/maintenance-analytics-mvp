import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle, Wrench, Activity } from 'lucide-react';
import {
  PieChart, Pie, Cell,
  Tooltip, ResponsiveContainer,
} from 'recharts';

const RISK_COLORS = {
  LOW: '#34d399',
  MEDIUM: '#fbbf24',
  HIGH: '#fb923c',
  CRITICAL: '#f87171',
};

const RISK_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

function StatCard({ title, value, icon, color }) {
  const gradients = {
    blue: 'from-blue-600 to-cyan-500',
    red: 'from-red-600 to-rose-500',
    orange: 'from-orange-500 to-amber-400',
  };
  return (
    <div className={`bg-gradient-to-br ${gradients[color]} rounded-lg p-4 shadow-md`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-white/70 uppercase tracking-wide">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className="bg-white/20 p-2 rounded">
          <div className="text-white">{icon}</div>
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ level }) {
  const styles = {
    LOW: 'bg-emerald-500/20 text-emerald-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    HIGH: 'bg-orange-500/20 text-orange-400',
    CRITICAL: 'bg-red-500/20 text-red-400',
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${styles[level] || 'bg-slate-500/20 text-slate-400'}`}>
      {level}
    </span>
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

  const highRisk = predictions.filter(p => p.risk_level === 'HIGH' || p.risk_level === 'CRITICAL');
  const critical = predictions.filter(p => p.risk_level === 'CRITICAL');

  const filtered = highRisk.filter(a =>
    !searchQuery || a.asset_id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const riskDistData = Object.entries(
    predictions.reduce((acc, p) => {
      acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
      return acc;
    }, {})
  )
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => RISK_ORDER.indexOf(a.name) - RISK_ORDER.indexOf(b.name));

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
    a.download = `high_risk_assets_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="w-full px-4 py-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <StatCard title="Total Monitored" value={predictions.length} icon={<Wrench className="w-5 h-5" />} color="blue" />
        <StatCard title="High Risk" value={highRisk.length} icon={<AlertCircle className="w-5 h-5" />} color="red" />
        <StatCard title="Critical" value={critical.length} icon={<Activity className="w-5 h-5" />} color="orange" />
      </div>

      {/* Risk Distribution Pie — full width, taller */}
      <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl mb-4" style={{ height: '350px' }}>
        <h2 className="text-sm font-semibold text-white mb-2">Risk Distribution</h2>
        {riskDistData.length > 0 ? (
          <ResponsiveContainer width="100%" height={290}>
            <PieChart>
              <Pie
                data={riskDistData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={110}
                isAnimationActive={true}
                animationDuration={800}
                label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#94a3b8' }}
              >
                {riskDistData.map(entry => (
                  <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#94a3b8'} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
                      <p className="font-semibold text-white mb-1">{payload[0].name}</p>
                      <p className="text-slate-300">{payload[0].value} assets</p>
                    </div>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
            No prediction data — run the pipeline first
          </div>
        )}
      </div>

      {/* High Risk Assets Table */}
      <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">
            High Risk Assets <span className="text-slate-500 font-normal">({filtered.length})</span>
          </h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search asset ID..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-1 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={exportCSV}
              className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded"
            >
              Export CSV
            </button>
          </div>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: '400px' }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900">
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left py-2 pr-4">Asset ID</th>
                <th className="text-left py-2 pr-4">Risk Level</th>
                <th className="text-right py-2 pr-4">Failure Prob.</th>
                <th className="text-right py-2 pr-4">Days to Failure</th>
                <th className="text-left py-2">Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">No high-risk assets found</td>
                </tr>
              ) : (
                filtered.map((asset, idx) => (
                  <tr key={idx} className="border-b border-slate-800 hover:bg-slate-800/40">
                    <td className="py-2 pr-4 text-slate-200 font-medium">{asset.asset_id}</td>
                    <td className="py-2 pr-4"><RiskBadge level={asset.risk_level} /></td>
                    <td className="py-2 pr-4 text-right text-slate-300">
                      {asset.failure_probability != null ? `${(asset.failure_probability * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="py-2 pr-4 text-right text-slate-300">
                      {asset.days_to_predicted_failure ?? 'N/A'}
                    </td>
                    <td className="py-2 text-slate-400 max-w-xs truncate">{asset.recommendation || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
