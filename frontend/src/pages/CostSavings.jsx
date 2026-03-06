import { useState, useEffect } from 'react';
import { getPredictions } from '../services/api';
import { AlertCircle, DollarSign } from 'lucide-react';
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function CostSavings({ dateRange }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [costSavings, setCostSavings] = useState([]);
  const [pmOptimization, setPmOptimization] = useState([]);

  useEffect(() => {
    load();
  }, [dateRange]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = dateRange ? { days: dateRange } : {};
      const [dashRes, pmRes] = await Promise.all([
        getPredictions.dashboard(),
        getPredictions.pmOptimization(params),
      ]);
      setCostSavings(dashRes.data?.cost_saving_opportunities || []);
      setPmOptimization(pmRes.data || []);
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

  const totalSavings = costSavings.reduce((sum, c) => sum + (c.estimated_cost_savings || 0), 0);

  const chartData = costSavings
    .filter(c => c.estimated_cost_savings > 0)
    .slice(0, 15)
    .map((c, i) => ({
      name: c.asset_id || `Asset ${i + 1}`,
      savings: Math.round(c.estimated_cost_savings),
    }));

  const exportPMCSV = () => {
    const headers = ['asset_id', 'current_pm_frequency_days', 'suggested_pm_frequency_days', 'estimated_cost_savings'];
    const csvContent = [
      headers.join(','),
      ...pmOptimization.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const str = String(val).replace(/"/g, '""');
        return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str}"` : str;
      }).join(','))
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pm_optimization_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="w-full px-4 py-4 h-full overflow-y-auto">
      {/* Total Savings Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="bg-gradient-to-br from-emerald-600 to-teal-500 rounded-lg p-4 shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-white/70 uppercase tracking-wide">Total Savings Potential</p>
              <p className="text-2xl font-bold text-white mt-1">${Math.round(totalSavings).toLocaleString()}</p>
            </div>
            <div className="bg-white/20 p-2 rounded">
              <div className="text-white"><DollarSign className="w-5 h-5" /></div>
            </div>
          </div>
        </div>
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Opportunities</p>
          <p className="text-2xl font-bold text-white">{costSavings.filter(c => c.estimated_cost_savings > 0).length}</p>
        </div>
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">PM Optimizations</p>
          <p className="text-2xl font-bold text-white">{pmOptimization.length}</p>
        </div>
      </div>

      {/* Cost Savings Area Chart — full width */}
      <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Savings by Asset</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 60 }}>
              <defs>
                <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="name"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                angle={-45}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
                      <p className="font-semibold text-white mb-1">{label}</p>
                      <p className="text-emerald-300">${payload[0].value.toLocaleString()} savings</p>
                    </div>
                  );
                }}
              />
              <Area type="monotone" dataKey="savings" stroke="#10b981" strokeWidth={2} fill="url(#savingsGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
            No cost savings data available
          </div>
        )}
      </div>

      {/* PM Optimization Table */}
      <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">
            PM Optimization <span className="text-slate-500 font-normal">({pmOptimization.length})</span>
          </h3>
          <button
            onClick={exportPMCSV}
            className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-1 rounded"
          >
            Export CSV
          </button>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: '400px' }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900">
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left py-2 pr-4">Asset</th>
                <th className="text-right py-2 pr-4">Current PM (days)</th>
                <th className="text-right py-2 pr-4">Suggested (days)</th>
                <th className="text-right py-2">Savings / yr</th>
              </tr>
            </thead>
            <tbody>
              {pmOptimization.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">No PM optimization data</td>
                </tr>
              ) : (
                pmOptimization.map((row, idx) => (
                  <tr key={idx} className="border-b border-slate-800 hover:bg-slate-800/40">
                    <td className="py-2 pr-4 text-slate-200 font-medium">{row.asset_id}</td>
                    <td className="py-2 pr-4 text-right text-slate-300">{row.current_pm_frequency_days ?? '—'}</td>
                    <td className="py-2 pr-4 text-right text-indigo-300">{row.suggested_pm_frequency_days ?? '—'}</td>
                    <td className="py-2 text-right text-emerald-400 font-semibold">
                      {row.estimated_cost_savings != null
                        ? `$${Math.round(row.estimated_cost_savings).toLocaleString()}`
                        : '—'}
                    </td>
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
