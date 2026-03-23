import { useState, useEffect } from 'react';
import { X, FileText, Download, Loader2, RefreshCw } from 'lucide-react';
import { generateReport } from '../services/api';
import { useAuth } from '../context/AuthContext';

const DEFAULT_SECTIONS = {
  overview: { label: 'Overview Summary', checked: true },
  asset_health: { label: 'Asset Health Breakdown', checked: true },
  critical_assets: { label: 'Critical & High Risk Assets', checked: true },
  pm_suggestions: { label: 'PM Recommendations', checked: false },
  insights: { label: 'AI Insights', checked: true },
};

export default function GenerateReportDrawer({ open, onClose, pageSections }) {
  const { syncing, lastSynced } = useAuth();
  const [sections, setSections] = useState(DEFAULT_SECTIONS);
  const [dateRange, setDateRange] = useState('30d');
  const [format, setFormat] = useState('pdf');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Apply page-specific section presets when opened
  useEffect(() => {
    if (open && pageSections) {
      setSections(prev => {
        const next = { ...prev };
        Object.entries(pageSections).forEach(([k, v]) => {
          if (next[k]) next[k] = { ...next[k], checked: v };
        });
        return next;
      });
    }
  }, [open, pageSections]);

  const toggle = (key) =>
    setSections(prev => ({ ...prev, [key]: { ...prev[key], checked: !prev[key].checked } }));

  const daysMap = { '7d': 7, '30d': 30, '90d': 90, 'all': null };

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    try {
      const selectedSections = Object.entries(sections)
        .filter(([, { checked }]) => checked)
        .map(([key]) => key);
      if (!selectedSections.length) {
        setError('Select at least one section.');
        return;
      }
      const { blob, filename } = await generateReport({
        sections: selectedSections,
        days: daysMap[dateRange],
        format,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      onClose();
    } catch (e) {
      setError(e.message || 'Failed to generate report.');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-96 bg-slate-900 border-l border-slate-700 z-50 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div className="flex items-center gap-2.5">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-semibold text-white">Generate Report</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {/* Sections */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Include Sections</p>
            <div className="space-y-1">
              {Object.entries(sections).map(([key, { label, checked }]) => (
                <label
                  key={key}
                  className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-800 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(key)}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-700 accent-indigo-500"
                  />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    {label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Date Range</p>
            <div className="grid grid-cols-4 gap-2">
              {[['7d','7d'],['30d','30d'],['90d','90d'],['all','All']].map(([v,l]) => (
                <button
                  key={v}
                  onClick={() => setDateRange(v)}
                  className={`py-2 rounded-lg text-xs font-medium transition-colors ${
                    dateRange === v
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                  }`}
                >{l}</button>
              ))}
            </div>
          </div>

          {/* Format */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Format</p>
            <div className="grid grid-cols-2 gap-2">
              {['pdf','csv'].map(f => (
                <button
                  key={f}
                  onClick={() => setFormat(f)}
                  className={`py-2 rounded-lg text-xs font-medium uppercase transition-colors ${
                    format === f
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                  }`}
                >{f}</button>
              ))}
            </div>
          </div>

          {/* Email delivery */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
              Email Delivery <span className="normal-case font-normal text-slate-500">(optional)</span>
            </p>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-700 space-y-2">
          {syncing && (
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <RefreshCw className="w-3 h-3 animate-spin text-indigo-400" />
              Sync in progress — report uses last synced data
            </p>
          )}
          {!syncing && lastSynced && (
            <p className="text-xs text-slate-500">
              Data as of {lastSynced.toLocaleTimeString()}
            </p>
          )}
          {error && (
            <p className="text-xs text-red-400 text-center pb-1">{error}</p>
          )}
          <button
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
            onClick={handleDownload}
            disabled={loading}
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Download className="w-4 h-4" />
            }
            {loading ? 'Generating…' : `Download ${format.toUpperCase()}`}
          </button>
        </div>
      </div>
    </>
  );
}
