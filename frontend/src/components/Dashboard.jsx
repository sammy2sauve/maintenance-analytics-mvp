import { useState, useEffect } from 'react';
import { getPredictions, getKPIs } from '../services/api';
import { AlertCircle, TrendingUp, DollarSign, Wrench, Activity } from 'lucide-react';

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [dailyKPIs, setDailyKPIs] = useState([]);
  const [dateRange, setDateRange] = useState(30);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load dashboard data and KPIs in parallel
      const [dashboardRes, kpisRes] = await Promise.all([
        getPredictions.dashboard(),
        getKPIs.daily({ limit: 10 })
      ]);

      setDashboardData(dashboardRes.data);
      setDailyKPIs(kpisRes.data);
    } catch (err) {
      setError(err.message);
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-600">
          <AlertCircle className="w-12 h-12 mx-auto mb-4" />
          <p>Error: {error}</p>
          <button 
            onClick={loadDashboard}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Maintenance Analytics Dashboard
          </h1>
          <p className="text-gray-600 mt-1">TrueSignal Intelligence Platform</p>
        </div>
      </header>

      {/* Date Range Filter */}
      <div className="bg-white shadow mb-6">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600 mr-2">Time Range:</span>
          {[7, 30, 90].map(days => (
            <button
              key={days}
              onClick={() => setDateRange(days)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                dateRange === days
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All Time
          </button>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Assets"
            value={summary.total_assets_monitored || 0}
            icon={<Wrench className="w-6 h-6" />}
            color="blue"
          />
          <StatCard
            title="High Risk Assets"
            value={summary.high_risk_assets || 0}
            icon={<AlertCircle className="w-6 h-6" />}
            color="red"
          />
          <StatCard
            title="Critical Risk"
            value={summary.critical_risk_assets || 0}
            icon={<Activity className="w-6 h-6" />}
            color="orange"
          />
          <StatCard
            title="Cost Savings"
            value={`$${(summary.total_cost_savings_potential || 0).toLocaleString()}`}
            icon={<DollarSign className="w-6 h-6" />}
            color="green"
          />
        </div>

        {/* KPIs Section */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Daily KPIs</h2>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      KPI Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Raw Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      TrueSignal Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Distortion
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dailyKPIs.map((kpi, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {kpi.kpi_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatValue(kpi.raw_value)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatValue(kpi.truesignal_value)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {kpi.distortion_flag ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                            Distorted
                          </span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            Clean
                          </span>
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
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">Latest Insights</h2>
              <button
                onClick={exportInsightsCSV}
                className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded-lg text-sm hover:bg-green-100 transition-colors"
              >
                <span>&#x2B07;</span> Export CSV
              </button>
            </div>
            <div className="p-6">
              {filteredInsights.map((insight, index) => (
                <div key={index} className="mb-4 last:mb-0 p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">{insight.title}</h3>
                  <p className="text-sm text-gray-600">{insight.description}</p>
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                    <span>Impact: {insight.impact_level}</span>
                    <span>Confidence: {(insight.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* High Risk Assets */}
        {highRisk.length > 0 && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">High Risk Assets</h2>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search assets..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="absolute left-2.5 top-2.5 text-gray-400 text-sm">&#x1F50D;</span>
                </div>
                <span className="text-sm text-gray-500">{filteredHighRisk.length} of {highRisk.length}</span>
                <button
                  onClick={exportHighRiskCSV}
                  className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded-lg text-sm hover:bg-green-100 transition-colors"
                >
                  <span>&#x2B07;</span> Export CSV
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid gap-4">
                {filteredHighRisk.map((asset, index) => (
                  <div key={index} className="p-4 border border-red-200 rounded-lg bg-red-50">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-gray-900">{asset.asset_id}</h3>
                        <p className="text-sm text-gray-600 mt-1">{asset.recommendation}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-red-600">
                          {(asset.failure_probability * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-gray-500">{asset.risk_level}</div>
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

// Helper Components
function StatCard({ title, value, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    green: 'bg-green-500',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`${colorClasses[color]} p-3 rounded-lg text-white`}>
          {icon}
        </div>
        <div className="ml-4">
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') {
    return value.toFixed(2);
  }
  return value;
}

export default Dashboard;