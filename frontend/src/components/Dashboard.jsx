import { useState, useEffect } from 'react';
import { getPredictions, getKPIs } from '../services/api';
import { AlertCircle, DollarSign, Wrench, Activity } from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area,
} from 'recharts';

const RISK_COLORS = {
  LOW: '#34d399',
  MEDIUM: '#fbbf24',
  HIGH: '#fb923c',
  CRITICAL: '#f87171',
};

const DarkTooltip = ({ children }) => (
  <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
    {children}
  </div>
);

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [dailyKPIs, setDailyKPIs] = useState([]);
  const [failurePredictions, setFailurePredictions] = useState([]);
  const [dateRange, setDateRange] = useState(30);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const [dashboardRes, kpisRes, predictionsRes] = await Promise.all([
        getPredictions.dashboard(),
        getKPIs.daily({ limit: 100 }),
        getPredictions.failures({ limit: 1000 }),
      ]);

      setDashboardData(dashboardRes.data);

      // Deduplicate: keep only the latest entry per kpi_name
      const kpiMap = new Map();
      (kpisRes.data || []).forEach(k => {
        if (!kpiMap.has(k.kpi_name) || k.period_date > kpiMap.get(k.kpi_name).period_date) {
          kpiMap.set(k.kpi_name, k);
        }
      });
      setDailyKPIs(Array.from(kpiMap.values()).sort((a, b) => a.kpi_name.localeCompare(b.kpi_name)));

      setFailurePredictions(predictionsRes.data);
    } catch (err) {
      setError(err.message);
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-slate-300 text-xl animate-pulse">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-red-400 text-center">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <p>Error: {error}</p>
          <button
            onClick={loadDashboard}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const summary = dashboardData?.summary || {};
  const insights = dashboardData?.latest_insights || [];
  const highRisk = dashboardData?.high_risk_assets || [];
  const costSavings = dashboardData?.cost_saving_opportunities || [];

  // --- Date + search filters ---
  const filteredInsights = dateRange
    ? insights.filter(i => {
        const d = new Date(i.insight_date);
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - dateRange);
        return d >= cutoff;
      })
    : insights;

  const filteredHighRisk = highRisk
    .filter(a => {
      if (!dateRange) return true;
      const d = new Date(a.prediction_date);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - dateRange);
      return d >= cutoff;
    })
    .filter(a => !searchQuery || a.asset_id.toLowerCase().includes(searchQuery.toLowerCase()));

  // --- CSV export ---
  const exportToCSV = (data, filename, headers) => {
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(h => {
        const key = h.toLowerCase().replace(/ /g, '_');
        const val = row[key] ?? row[h] ?? '';
        const str = String(val).replace(/"/g, '""');
        return str.includes(',') || str.includes('"') || str.includes('\n')
          ? `"${str}"` : str;
      }).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportInsightsCSV = () => {
    exportToCSV(
      filteredInsights,
      `insights_${new Date().toISOString().split('T')[0]}.csv`,
      ['title', 'description', 'impact_level', 'confidence_score', 'insight_type', 'insight_date']
    );
  };

  const exportHighRiskCSV = () => {
    exportToCSV(
      filteredHighRisk,
      `high_risk_assets_${new Date().toISOString().split('T')[0]}.csv`,
      ['asset_id', 'risk_level', 'failure_probability', 'recommendation', 'days_to_predicted_failure', 'prediction_date']
    );
  };

  // --- Chart data ---
  const riskDistData = Object.entries(
    failurePredictions.reduce((acc, p) => {
      acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
      return acc;
    }, {})
  )
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(a.name) - ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(b.name));

  const costSavingsData = costSavings
    .filter(c => c.estimated_cost_savings > 0)
    .slice(0, 10)
    .map(c => ({
      asset_id: c.asset_id,
      savings: Math.round(c.estimated_cost_savings),
      current_freq: c.current_pm_frequency_days,
      suggested_freq: c.suggested_pm_frequency_days,
    }));

  const kpiByName = {};
  dailyKPIs.forEach(k => { if (!kpiByName[k.kpi_name]) kpiByName[k.kpi_name] = k; });
  const kpiCompareData = Object.values(kpiByName).map(k => ({
    name: k.kpi_name
      .replace(' (True)', '')
      .replace('Mean Time to Complete', 'MTTC')
      .replace('Labor Utilization', 'Labor Util')
      .replace('Maintenance Load Stability', 'Maint Load')
      .replace('Failure Recurrence Index', 'Failure Recur'),
    raw: k.raw_value != null ? +k.raw_value.toFixed(2) : 0,
    truesignal: k.truesignal_value != null ? +k.truesignal_value.toFixed(2) : 0,
    distorted: k.distortion_flag,
  }));

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border-b border-indigo-800/30 shadow-2xl">
        <div className="w-full px-8 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Maintenance Analytics</h1>
            <p className="text-indigo-300 mt-1 text-sm font-medium">TrueSignal Intelligence Platform</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <span className="text-emerald-300 text-sm font-medium">Live</span>
          </div>
        </div>
      </header>

      {/* Date Range Filter */}
      <div className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 mb-6 sticky top-0 z-10">
        <div className="w-full px-8 py-3 flex items-center gap-3">
          <span className="text-sm font-medium text-slate-400 mr-2">Time Range:</span>
          {[7, 30, 90].map(days => (
            <button
              key={days}
              onClick={() => setDateRange(days)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                dateRange === days
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Last {days} Days
            </button>
          ))}
          <button
            onClick={() => setDateRange(null)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              dateRange === null
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            All Time
          </button>
        </div>
      </div>

      <main className="w-full px-8 py-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard title="Total Assets" value={summary.total_assets_monitored || 0} icon={<Wrench className="w-6 h-6" />} color="blue" />
          <StatCard title="High Risk Assets" value={summary.high_risk_assets || 0} icon={<AlertCircle className="w-6 h-6" />} color="red" />
          <StatCard title="Critical Risk" value={summary.critical_risk_assets || 0} icon={<Activity className="w-6 h-6" />} color="orange" />
          <StatCard title="Cost Savings" value={`$${(summary.total_cost_savings_potential || 0).toLocaleString()}`} icon={<DollarSign className="w-6 h-6" />} color="green" />
        </div>

        {/* Charts Row 1: Risk Distribution + Top Failing Assets */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* Chart 1: Risk Distribution */}
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6 shadow-2xl hover:border-indigo-500/30 transition-all duration-300">
            <h2 className="text-lg font-semibold text-white mb-4">Asset Risk Distribution</h2>
            {riskDistData.length > 0 ? (
              <ResponsiveContainer width="100%" height={380}>
                <PieChart>
                  <Pie
                    data={riskDistData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
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
                  <Legend formatter={v => <span style={{ color: '#94a3b8' }}>{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
                No prediction data — run the pipeline first
              </div>
            )}
          </div>

          {/* Chart 2: Maintenance Health Gauge */}
          <MaintenanceHealthGauge summary={summary} kpis={dailyKPIs} />
        </div>

        {/* Chart 3: Cost Savings */}
        {costSavingsData.length > 0 && (
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6 mb-6 shadow-2xl hover:border-indigo-500/30 transition-all duration-300">
            <h2 className="text-lg font-semibold text-white mb-4">Cost Savings Opportunities — PM Optimization</h2>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={costSavingsData} margin={{ left: 10, right: 10 }}>
                <defs>
                  <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                <XAxis dataKey="asset_id" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={{ stroke: '#475569' }} />
                <YAxis tickFormatter={v => `$${v.toLocaleString()}`} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={{ stroke: '#475569' }} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
                        <p className="font-semibold text-white mb-1">{d.asset_id}</p>
                        <p className="text-slate-300">Savings: <span className="font-medium text-emerald-400">${d.savings.toLocaleString()}/yr</span></p>
                        <p className="text-slate-400">Current PM every {d.current_freq} days</p>
                        <p className="text-slate-400">Suggested every {d.suggested_freq} days</p>
                      </div>
                    );
                  }}
                />
                <Area type="monotone" dataKey="savings" stroke="#10b981" fill="url(#costGradient)" strokeWidth={2} animationDuration={800} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Chart 4: KPI Raw vs TrueSignal */}
        {kpiCompareData.length > 0 && (
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6 mb-6 shadow-2xl hover:border-indigo-500/30 transition-all duration-300">
            <h2 className="text-lg font-semibold text-white mb-1">KPI Raw vs TrueSignal Values</h2>
            <p className="text-xs text-slate-500 mb-4">TrueSignal engine removes distortion from raw maintenance metrics</p>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={kpiCompareData} margin={{ left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={{ stroke: '#475569' }} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={{ stroke: '#475569' }} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const d = kpiCompareData.find(k => k.name === label);
                    return (
                      <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl text-xs">
                        <p className="font-semibold text-white mb-1">{label}</p>
                        {payload.map(p => (
                          <p key={p.dataKey} style={{ color: p.fill }} className="text-slate-300">
                            {p.name}: {p.value}
                          </p>
                        ))}
                        {d?.distorted && (
                          <p className="text-orange-400 mt-1 font-medium">⚠ Distortion detected</p>
                        )}
                      </div>
                    );
                  }}
                />
                <Legend formatter={v => <span style={{ color: '#94a3b8' }}>{v}</span>} />
                <Bar dataKey="raw" name="Raw" fill="#475569" radius={[4, 4, 0, 0]} animationDuration={800} />
                <Bar dataKey="truesignal" name="TrueSignal" fill="#818cf8" radius={[4, 4, 0, 0]} animationDuration={800} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* KPIs Table */}
        <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl mb-6">
          <div className="px-6 py-4 border-b border-slate-700/50">
            <h2 className="text-xl font-semibold text-white">Daily KPIs</h2>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-700/50">
                <thead>
                  <tr className="bg-slate-800/60">
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">KPI Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Raw Value</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">TrueSignal Value</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Distortion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {dailyKPIs.map((kpi, index) => (
                    <tr key={index} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">{kpi.kpi_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">{formatValue(kpi.raw_value)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-indigo-300 font-medium">{formatValue(kpi.truesignal_value)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {kpi.distortion_flag ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-900/50 text-red-300 border border-red-700/50">Distorted</span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-900/50 text-emerald-300 border border-emerald-700/50">Clean</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Insights */}
        {insights.length > 0 && (
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl mb-6">
            <div className="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-white">Latest Insights</h2>
              <button
                onClick={exportInsightsCSV}
                className="flex items-center gap-2 px-3 py-1.5 bg-emerald-900/40 text-emerald-300 border border-emerald-700/50 rounded-lg text-sm hover:bg-emerald-900/60 transition-colors"
              >
                &#x2B07; Export CSV
              </button>
            </div>
            <div className="p-6">
              {filteredInsights.length === 0 ? (
                <p className="text-slate-500 text-sm">No insights in selected time range.</p>
              ) : (
                filteredInsights.map((insight, index) => (
                  <div key={index} className="mb-4 last:mb-0 p-4 bg-indigo-950/50 border border-indigo-800/30 rounded-xl">
                    <h3 className="font-semibold text-white mb-2">{insight.title}</h3>
                    <p className="text-sm text-slate-400">{insight.description}</p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                      <span>Impact: <span className="text-indigo-300">{insight.impact_level}</span></span>
                      <span>Confidence: <span className="text-indigo-300">{(insight.confidence_score * 100).toFixed(0)}%</span></span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* High Risk Assets */}
        {highRisk.length > 0 && (
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-white">High Risk Assets</h2>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search assets..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="pl-8 pr-4 py-2 bg-slate-800 border border-slate-600 text-slate-200 placeholder-slate-500 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="absolute left-2.5 top-2.5 text-slate-500 text-sm">&#x1F50D;</span>
                </div>
                <span className="text-sm text-slate-500">{filteredHighRisk.length} of {highRisk.length}</span>
                <button
                  onClick={exportHighRiskCSV}
                  className="flex items-center gap-2 px-3 py-1.5 bg-emerald-900/40 text-emerald-300 border border-emerald-700/50 rounded-lg text-sm hover:bg-emerald-900/60 transition-colors"
                >
                  &#x2B07; Export CSV
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid gap-3">
                {filteredHighRisk.map((asset, index) => (
                  <div key={index} className="p-4 bg-red-950/40 border border-red-800/30 rounded-xl hover:border-red-600/40 transition-colors">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-white">{asset.asset_id}</h3>
                        <p className="text-sm text-slate-400 mt-1">{asset.recommendation}</p>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-2xl font-bold text-red-400">
                          {(asset.failure_probability * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-slate-500">{asset.risk_level}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  const gradients = {
    blue: 'from-blue-600 to-cyan-500',
    red: 'from-red-600 to-rose-500',
    orange: 'from-orange-500 to-amber-400',
    green: 'from-emerald-600 to-teal-500',
  };
  const glows = {
    blue: 'shadow-blue-500/20',
    red: 'shadow-red-500/20',
    orange: 'shadow-orange-500/20',
    green: 'shadow-emerald-500/20',
  };

  return (
    <div className={`bg-gradient-to-br ${gradients[color]} rounded-2xl p-6 shadow-2xl ${glows[color]} hover:scale-105 transition-all duration-300 cursor-pointer`}>
      <div className="flex items-center justify-between mb-4">
        <div className="bg-white/20 backdrop-blur-sm p-3 rounded-xl">
          <div className="text-white">{icon}</div>
        </div>
        <div className="text-white/70 text-xs font-medium uppercase tracking-wider text-right">{title}</div>
      </div>
      <div className="text-4xl font-bold text-white">{value}</div>
    </div>
  );
}

function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') return value.toFixed(2);
  return value;
}

function MaintenanceHealthGauge({ summary, kpis }) {
  const criticalCount = summary?.critical_risk_assets || 0;
  const highCount = summary?.high_risk_assets || 0;
  const costSavings = summary?.total_cost_savings_potential || 0;

  const pmKpi = kpis?.find(k =>
    k.kpi_name?.toLowerCase().includes('pm') ||
    k.kpi_name?.toLowerCase().includes('preventive')
  );
  const pmRate = pmKpi ? (pmKpi.truesignal_value || pmKpi.raw_value || 0) : 0;

  let score = 50;
  score -= criticalCount * 3;
  score -= highCount * 1;
  score += Math.min(costSavings / 10000, 15);
  if (pmRate > 0.7) score += 5;
  score = Math.max(0, Math.min(100, Math.round(score)));

  const getZone = (s) => {
    if (s < 40) return { label: 'REACTIVE', color: '#ef4444', bg: 'from-red-900/40 to-red-800/20', border: 'border-red-700/50' };
    if (s < 70) return { label: 'IMPROVING', color: '#f59e0b', bg: 'from-amber-900/40 to-amber-800/20', border: 'border-amber-700/50' };
    return { label: 'PROACTIVE', color: '#10b981', bg: 'from-emerald-900/40 to-emerald-800/20', border: 'border-emerald-700/50' };
  };

  const zone = getZone(score);

  // Larger gauge — arc center near bottom of viewBox so semicircle fills space
  const cx = 200, cy = 190;
  const innerR = 118, outerR = 168;

  const polarToCartesian = (angleDeg, radius) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy - radius * Math.sin(rad) };
  };

  const arcPath = (startDeg, endDeg, inner, outer) => {
    const s = polarToCartesian(startDeg, outer);
    const e = polarToCartesian(endDeg, outer);
    const si = polarToCartesian(startDeg, inner);
    const ei = polarToCartesian(endDeg, inner);
    const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${outer} ${outer} 0 ${large} 0 ${e.x} ${e.y} L ${ei.x} ${ei.y} A ${inner} ${inner} 0 ${large} 1 ${si.x} ${si.y} Z`;
  };

  const needleAngle = 180 - (score / 100) * 180;
  const needleTip = polarToCartesian(needleAngle, outerR);

  return (
    <div className={`bg-gradient-to-br ${zone.bg} backdrop-blur-sm border ${zone.border} rounded-2xl p-6 shadow-2xl transition-all duration-300`}>
      <h2 className="text-lg font-semibold text-white mb-1">Maintenance Health Score</h2>
      <p className="text-sm text-slate-400 mb-3">Overall operational health based on risk profile &amp; savings potential</p>
      <div className="flex flex-col items-center w-full">
        {/* SVG gauge — score/label live in HTML below, no SVG text overlap */}
        <svg width="100%" viewBox="0 0 400 200" style={{ display: 'block' }}>
          {/* Background track */}
          <path d={arcPath(0, 180, innerR, outerR)} fill="#1e293b" stroke="#000" strokeWidth="3" />
          {/* Red zone 0–40: angles 180→108 */}
          <path d={arcPath(108, 180, innerR + 1, outerR - 1)} fill="#ef4444" opacity="0.9" stroke="#000" strokeWidth="2" />
          {/* Yellow zone 40–70: angles 108→54 */}
          <path d={arcPath(54, 108, innerR + 1, outerR - 1)} fill="#f59e0b" opacity="0.9" stroke="#000" strokeWidth="2" />
          {/* Green zone 70–100: angles 54→0 */}
          <path d={arcPath(0, 54, innerR + 1, outerR - 1)} fill="#10b981" opacity="0.9" stroke="#000" strokeWidth="2" />
          {/* Score fill arc (current position) */}
          {score > 0 && (
            <path d={arcPath(needleAngle, 180, innerR + 2, outerR - 2)} fill={zone.color} />
          )}
          {/* Needle — white outline + white core */}
          <line x1={cx} y1={cy} x2={needleTip.x} y2={needleTip.y} stroke="#000" strokeWidth="7" strokeLinecap="round" />
          <line x1={cx} y1={cy} x2={needleTip.x} y2={needleTip.y} stroke="#fff" strokeWidth="3.5" strokeLinecap="round" />
          {/* Pivot cap */}
          <circle cx={cx} cy={cy} r="16" fill="#1e293b" stroke="#000" strokeWidth="3" />
          <circle cx={cx} cy={cy} r="9" fill={zone.color} stroke="#000" strokeWidth="1.5" />
        </svg>

        {/* Score display — HTML below SVG, no overlap */}
        <div className="text-center mt-2">
          <div className="text-7xl font-bold text-white leading-none">{score}</div>
          <div className="text-2xl font-bold mt-2" style={{ color: zone.color }}>{zone.label}</div>
        </div>

        {/* Zone legend */}
        <div className="flex gap-4 mt-5">
          {[
            { color: '#ef4444', label: '0–40 Reactive' },
            { color: '#f59e0b', label: '40–70 Improving' },
            { color: '#10b981', label: '70–100 Proactive' },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1.5 text-sm font-medium text-slate-200">
              <span className="w-3.5 h-3.5 rounded-sm inline-block border border-black/60 flex-shrink-0" style={{ background: color }} />
              {label}
            </span>
          ))}
        </div>

        {/* Score breakdown */}
        <div className="flex gap-5 mt-3 text-sm text-slate-300">
          <span>Critical: <span className="text-red-400 font-semibold">-{criticalCount * 3}</span></span>
          <span>High Risk: <span className="text-orange-400 font-semibold">-{highCount}</span></span>
          <span>Savings: <span className="text-emerald-400 font-semibold">+{Math.round(Math.min(costSavings / 10000, 15))}</span></span>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
