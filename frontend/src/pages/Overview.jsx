import { useState, useEffect } from 'react';
import { getPredictions, getKPIs } from '../services/api';
import { AlertCircle, Wrench, Activity, FileText, Bell } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import EmptyState from '../components/EmptyState';
import GenerateReportDrawer from '../components/GenerateReportDrawer';
import NotifyMeDrawer from '../components/NotifyMeDrawer';
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
    <div className={`bg-gradient-to-br ${gradients[color]} rounded-lg p-4 shadow-md ${glows[color]}`}>
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

function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') return value.toFixed(2);
  return value;
}

function MaintenanceHealthGauge({ summary, kpis }) {
  const criticalCount = summary?.critical_risk_assets || 0;
  const highCount = summary?.high_risk_assets || 0;

  const pmKpi = kpis?.find(k =>
    k.kpi_name?.toLowerCase().includes('pm') ||
    k.kpi_name?.toLowerCase().includes('preventive')
  );
  const pmRate = pmKpi ? (pmKpi.truesignal_value || pmKpi.raw_value || 0) : 0;

  let score = 50;
  score -= criticalCount * 3;
  score -= highCount * 1;
  if (pmRate > 0.7) score += 5;
  score = Math.max(0, Math.min(100, Math.round(score)));

  const getZone = (s) => {
    if (s < 40) return { label: 'REACTIVE', color: '#ef4444', bg: 'from-red-900/40 to-red-800/20', border: 'border-red-700/50' };
    if (s < 70) return { label: 'IMPROVING', color: '#f59e0b', bg: 'from-amber-900/40 to-amber-800/20', border: 'border-amber-700/50' };
    return { label: 'PROACTIVE', color: '#10b981', bg: 'from-emerald-900/40 to-emerald-800/20', border: 'border-emerald-700/50' };
  };

  const zone = getZone(score);

  const cx = 200, cy = 178;
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
    <div className={`bg-gradient-to-br ${zone.bg} backdrop-blur-sm border ${zone.border} rounded-2xl p-3 shadow-2xl transition-all duration-300`} style={{ height: '250px', overflow: 'hidden' }}>
      <h2 className="text-sm font-semibold text-white mb-1">Maintenance Health</h2>
      <div className="flex flex-col items-center w-full">
        <svg width="100%" viewBox="0 0 400 200" style={{ display: 'block', maxHeight: '130px' }}>
          <path d={arcPath(0, 180, innerR, outerR)} fill="#1e293b" stroke="#000" strokeWidth="3" />
          <path d={arcPath(108, 180, innerR + 1, outerR - 1)} fill="#ef4444" opacity="0.9" stroke="#000" strokeWidth="2" />
          <path d={arcPath(54, 108, innerR + 1, outerR - 1)} fill="#f59e0b" opacity="0.9" stroke="#000" strokeWidth="2" />
          <path d={arcPath(0, 54, innerR + 1, outerR - 1)} fill="#10b981" opacity="0.9" stroke="#000" strokeWidth="2" />
          {score > 0 && (
            <path d={arcPath(needleAngle, 180, innerR + 2, outerR - 2)} fill={zone.color} />
          )}
          <line x1={cx} y1={cy} x2={needleTip.x} y2={needleTip.y} stroke="#000" strokeWidth="7" strokeLinecap="round" />
          <line x1={cx} y1={cy} x2={needleTip.x} y2={needleTip.y} stroke="#fff" strokeWidth="3.5" strokeLinecap="round" />
          <circle cx={cx} cy={cy} r="16" fill="#1e293b" stroke="#000" strokeWidth="3" />
          <circle cx={cx} cy={cy} r="9" fill={zone.color} stroke="#000" strokeWidth="1.5" />
        </svg>
        <div className="text-center mt-1">
          <div className="text-3xl font-bold text-white leading-none">{score}</div>
          <div className="text-sm font-bold mt-1" style={{ color: zone.color }}>{zone.label}</div>
        </div>
        <div className="flex gap-3 mt-2 text-xs text-slate-400">
          <span>Crit: <span className="text-red-400 font-semibold">-{criticalCount * 3}</span></span>
          <span>High: <span className="text-orange-400 font-semibold">-{highCount}</span></span>
        </div>
      </div>
    </div>
  );
}

function CompactKPITable({ kpis }) {
  const topKPIs = kpis.slice(0, 5);

  return (
    <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl" style={{ height: '250px' }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Key Metrics</h3>
        <span className="text-xs text-slate-400">{kpis.length} total</span>
      </div>
      <div className="space-y-2 overflow-y-auto" style={{ maxHeight: '195px' }}>
        {topKPIs.map((kpi, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-slate-700/30">
            <span className="text-slate-300 truncate mr-2">{kpi.kpi_name}</span>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-indigo-300 font-medium">{formatValue(kpi.truesignal_value)}</span>
              {kpi.distortion_flag && (
                <span className="text-yellow-400 text-[10px]">&#x26A0;</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightsPreview({ insights, onExport }) {
  return (
    <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Latest Insights <span className="text-slate-500 font-normal">({insights.length})</span></h3>
        {onExport && (
          <button
            onClick={onExport}
            className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded"
          >
            Export CSV
          </button>
        )}
      </div>
      {insights.length === 0 ? (
        <p className="text-xs text-slate-500 py-4 text-center">No insights yet — run the pipeline to generate patterns.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {insights.map((insight, idx) => (
            <div key={idx} className="border-l-2 border-indigo-500 pl-2 py-1">
              <p className="text-xs text-white font-medium leading-tight">{insight.title}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  insight.impact_level === 'HIGH' ? 'bg-red-500/20 text-red-400' :
                  insight.impact_level === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {insight.impact_level}
                </span>
                <span className="text-[10px] text-slate-400">
                  {(insight.confidence_score * 100).toFixed(0)}% conf
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Overview({ dateRange }) {
  const { hasApiKey, locationId, syncVersion } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [dailyKPIs, setDailyKPIs] = useState([]);
  const [failurePredictions, setFailurePredictions] = useState([]);
  const [reportOpen, setReportOpen] = useState(false);
  const [notifyOpen, setNotifyOpen] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);

      const timeParams = dateRange ? { days: dateRange } : {};
      const locParam = locationId ? { location_id: locationId } : {};
      const [dashboardRes, kpisRes, predictionsRes] = await Promise.all([
        getPredictions.dashboard(),
        getKPIs.daily({ limit: 100, ...timeParams, ...locParam }),
        getPredictions.failures({ limit: 1000, ...timeParams, ...locParam }),
      ]);

      setDashboardData(dashboardRes.data);

      const kpiMap = new Map();
      (kpisRes.data || []).forEach(k => {
        if (!kpiMap.has(k.kpi_name) || k.period_date > kpiMap.get(k.kpi_name).period_date) {
          kpiMap.set(k.kpi_name, k);
        }
      });
      setDailyKPIs(Array.from(kpiMap.values()).sort((a, b) => a.kpi_name.localeCompare(b.kpi_name)));
      // Deduplicate to latest prediction per asset within the date window
      const latestByAsset = new Map();
      (predictionsRes.data || []).forEach(p => {
        const existing = latestByAsset.get(p.asset_id);
        if (!existing || (p.prediction_date ?? '') > (existing.prediction_date ?? '')) {
          latestByAsset.set(p.asset_id, p);
        }
      });
      setFailurePredictions(Array.from(latestByAsset.values()));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasApiKey) load();
  }, [dateRange, hasApiKey, syncVersion]);

  if (!hasApiKey) return <EmptyState />;

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

  const summary = dashboardData?.summary || {};
  const insights = dashboardData?.latest_insights || [];

  const filteredSummary = {
    total_assets_monitored: failurePredictions.length,
    high_risk_assets: failurePredictions.filter(p => p.risk_level === 'HIGH' || p.risk_level === 'CRITICAL').length,
    critical_risk_assets: failurePredictions.filter(p => p.risk_level === 'CRITICAL').length,
  };

  const filteredInsights = dateRange
    ? insights.filter(i => {
        const d = new Date(i.insight_date);
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - dateRange);
        return d >= cutoff;
      })
    : insights;

  const riskDistData = Object.entries(
    failurePredictions.reduce((acc, p) => {
      acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
      return acc;
    }, {})
  )
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(a.name) - ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(b.name));

  const exportInsightsCSV = () => {
    const headers = ['title', 'description', 'impact_level', 'confidence_score', 'insight_type', 'insight_date'];
    const csvContent = [
      headers.join(','),
      ...filteredInsights.map(row => headers.map(h => {
        const val = row[h] ?? '';
        const str = String(val).replace(/"/g, '""');
        return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str}"` : str;
      }).join(','))
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insights_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="w-full px-4 py-4 h-full overflow-y-auto">
      <GenerateReportDrawer
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        pageSections={{ overview: true, asset_health: true, critical_assets: true, insights: true }}
      />
      <NotifyMeDrawer
        open={notifyOpen}
        onClose={() => setNotifyOpen(false)}
        page="overview"
      />

      {/* Page toolbar */}
      <div className="flex items-center justify-end gap-2 mb-3">
        <button
          onClick={() => setNotifyOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:border-amber-500/50 transition-colors"
        >
          <Bell className="w-3.5 h-3.5" />
          Notify Me
        </button>
        <button
          onClick={() => setReportOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:border-indigo-500/50 transition-colors"
        >
          <FileText className="w-3.5 h-3.5" />
          Generate Report
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <StatCard title="Total Assets" value={filteredSummary.total_assets_monitored} icon={<Wrench className="w-5 h-5" />} color="blue" />
        <StatCard title="High Risk Assets" value={filteredSummary.high_risk_assets} icon={<AlertCircle className="w-5 h-5" />} color="red" />
        <StatCard title="Critical Risk" value={filteredSummary.critical_risk_assets} icon={<Activity className="w-5 h-5" />} color="orange" />
      </div>

      {/* Charts Row: Risk Distribution + Health Gauge + KPI Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 shadow-2xl hover:border-indigo-500/30 transition-all duration-300" style={{ height: '250px', overflow: 'hidden' }}>
          <h2 className="text-sm font-semibold text-white mb-2">Risk Distribution</h2>
          {riskDistData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={riskDistData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={65}
                  isAnimationActive={true}
                  animationDuration={800}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
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
            <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
              No prediction data — run the pipeline first
            </div>
          )}
        </div>

        <MaintenanceHealthGauge summary={filteredSummary} kpis={dailyKPIs} />
        <CompactKPITable kpis={dailyKPIs} />
      </div>

      {/* Insights Preview */}
      <InsightsPreview insights={filteredInsights} onExport={exportInsightsCSV} />
    </main>
  );
}
