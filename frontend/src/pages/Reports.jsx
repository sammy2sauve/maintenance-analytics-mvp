import { useState } from 'react';
import {
  FileText, Bell, BookOpen,
  Plus, Trash2, ToggleLeft, ToggleRight,
  Download, Mail, Calendar, AlertTriangle, Loader2
} from 'lucide-react';
import { generateReport } from '../services/api';

// ── Stub data ────────────────────────────────────────────────────────────────
const SCHEDULED_REPORTS = [
  { id: 1, name: 'Weekly Asset Health Summary', frequency: 'Weekly', day: 'Monday', recipients: 'team@meridianmedical.org', active: true, lastRun: '2026-03-09' },
  { id: 2, name: 'Monthly KPI Dashboard', frequency: 'Monthly', day: '1st', recipients: 'director@meridianmedical.org', active: true, lastRun: '2026-03-01' },
  { id: 3, name: 'Critical Asset Digest', frequency: 'Daily', day: '—', recipients: 'ops@meridianmedical.org', active: false, lastRun: '2026-03-05' },
];

const ALERT_RULES = [
  { id: 1, name: 'Critical Risk Asset', condition: 'Any asset reaches CRITICAL risk', channel: 'Email', active: true },
  { id: 2, name: 'High Savings Threshold', condition: 'PM savings opportunity > $5,000', channel: 'Email', active: true },
  { id: 3, name: 'Overdue Maintenance', condition: 'Asset has no WO for 90+ days', channel: 'Email', active: false },
];

const NOTIFICATION_LOG = [
  { id: 1, type: 'alert', title: 'Critical Risk: MMC-AHU-003', message: 'Air Handling Unit 3 has reached CRITICAL risk level (score: 0.798)', time: '2026-03-11 08:42', read: false },
  { id: 2, type: 'report', title: 'Weekly Asset Health Summary sent', message: 'Report delivered to team@meridianmedical.org (29 assets, 2 critical)', time: '2026-03-09 07:00', read: true },
  { id: 3, type: 'alert', title: 'Critical Risk: MMC-CHIL-001', message: 'Chiller 1 has reached CRITICAL risk level (score: 0.812)', time: '2026-03-08 14:15', read: true },
  { id: 4, type: 'report', title: 'Monthly KPI Dashboard sent', message: 'Report delivered to director@meridianmedical.org', time: '2026-03-01 07:00', read: true },
];

const REPORT_SECTIONS = [
  { id: 'overview', label: 'Overview Summary', checked: true },
  { id: 'asset_health', label: 'Asset Health Breakdown', checked: true },
  { id: 'critical_assets', label: 'Critical & High Risk Assets', checked: true },
  { id: 'pm_suggestions', label: 'PM Recommendations', checked: false },
  { id: 'insights', label: 'AI Insights', checked: true },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
          <Icon className="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

const DAYS_MAP = { '7d': 7, '30d': 30, '90d': 90, 'all': null };

function ReportBuilder() {
  const [sections, setSections] = useState(REPORT_SECTIONS);
  const [dateRange, setDateRange] = useState('30d');
  const [format, setFormat] = useState('pdf');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const toggle = (id) => setSections(prev =>
    prev.map(s => s.id === id ? { ...s, checked: !s.checked } : s)
  );

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    try {
      const selected = sections.filter(s => s.checked).map(s => s.id);
      if (!selected.length) { setError('Select at least one section.'); return; }
      const { blob, filename } = await generateReport({
        sections: selected,
        days: DAYS_MAP[dateRange],
        format,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || 'Failed to generate report.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <SectionHeader icon={FileText} title="Report Builder" subtitle="Customize and export a one-time report" />

      <div className="grid grid-cols-2 gap-6">
        {/* Left: sections */}
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Include Sections</p>
          <div className="space-y-2">
            {sections.map(s => (
              <label key={s.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-700/40 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={s.checked}
                  onChange={() => toggle(s.id)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 accent-indigo-500"
                />
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">{s.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Right: options */}
        <div className="space-y-5">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Date Range</p>
            <div className="flex gap-2">
              {[['7d','7 days'],['30d','30 days'],['90d','90 days'],['all','All time']].map(([v,l]) => (
                <button
                  key={v}
                  onClick={() => setDateRange(v)}
                  className={`flex-1 py-1.5 rounded text-xs font-medium transition-colors ${
                    dateRange === v
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >{l}</button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Format</p>
            <div className="flex gap-2">
              {['pdf','csv'].map(f => (
                <button
                  key={f}
                  onClick={() => setFormat(f)}
                  className={`flex-1 py-1.5 rounded text-xs font-medium uppercase transition-colors ${
                    format === f
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >{f}</button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          <div className="pt-2">
            <button
              onClick={handleDownload}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Download className="w-4 h-4" />
              }
              {loading ? 'Generating…' : `Download ${format.toUpperCase()}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScheduledReports() {
  const [reports, setReports] = useState(SCHEDULED_REPORTS);

  const toggleActive = (id) => setReports(prev =>
    prev.map(r => r.id === id ? { ...r, active: !r.active } : r)
  );

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <SectionHeader
        icon={Calendar}
        title="Scheduled Reports"
        subtitle="Automated reports delivered on a recurring schedule"
        action={
          <button className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
            <Plus className="w-3.5 h-3.5" />
            Add schedule
          </button>
        }
      />

      <div className="space-y-3">
        {reports.map(r => (
          <div key={r.id} className="flex items-center gap-4 p-3.5 rounded-lg bg-slate-700/30 border border-slate-700/50">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{r.name}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {r.frequency} · {r.recipients} · Last run: {r.lastRun}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={() => toggleActive(r.id)}
                className={`transition-colors ${r.active ? 'text-emerald-400 hover:text-emerald-300' : 'text-slate-600 hover:text-slate-400'}`}
              >
                {r.active ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
              </button>
              <button className="text-slate-600 hover:text-red-400 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AlertRules() {
  const [rules, setRules] = useState(ALERT_RULES);

  const toggleActive = (id) => setRules(prev =>
    prev.map(r => r.id === id ? { ...r, active: !r.active } : r)
  );

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <SectionHeader
        icon={Bell}
        title="Alert Rules"
        subtitle="Get notified when conditions are met"
        action={
          <button className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
            <Plus className="w-3.5 h-3.5" />
            Add rule
          </button>
        }
      />

      <div className="space-y-3">
        {rules.map(r => (
          <div key={r.id} className="flex items-center gap-4 p-3.5 rounded-lg bg-slate-700/30 border border-slate-700/50">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white">{r.name}</p>
              <p className="text-xs text-slate-400 mt-0.5">{r.condition} · via {r.channel}</p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={() => toggleActive(r.id)}
                className={`transition-colors ${r.active ? 'text-emerald-400 hover:text-emerald-300' : 'text-slate-600 hover:text-slate-400'}`}
              >
                {r.active ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
              </button>
              <button className="text-slate-600 hover:text-red-400 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function NotificationLog() {
  const typeIcon = {
    alert: <AlertTriangle className="w-4 h-4 text-amber-400" />,
    report: <FileText className="w-4 h-4 text-indigo-400" />,
  };

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <SectionHeader
        icon={BookOpen}
        title="Notification Log"
        subtitle="Recent alerts and report deliveries"
      />

      <div className="space-y-3">
        {NOTIFICATION_LOG.map(n => (
          <div
            key={n.id}
            className={`flex items-start gap-3 p-3.5 rounded-lg border transition-colors ${
              n.read
                ? 'bg-slate-700/20 border-slate-700/40'
                : 'bg-indigo-500/5 border-indigo-500/20'
            }`}
          >
            <div className="mt-0.5 shrink-0">{typeIcon[n.type]}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className={`text-sm font-medium ${n.read ? 'text-slate-300' : 'text-white'}`}>
                  {n.title}
                </p>
                {!n.read && (
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5 truncate">{n.message}</p>
              <p className="text-[11px] text-slate-500 mt-1">{n.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Reports() {
  return (
    <div className="h-full overflow-y-auto"><div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Reports &amp; Alerts</h1>
          <p className="text-sm text-slate-400 mt-0.5">Build reports, schedule deliveries, and manage alert rules</p>
        </div>
      </div>

      {/* Top row: Report Builder + Scheduled Reports */}
      <div className="grid grid-cols-2 gap-6">
        <ReportBuilder />
        <ScheduledReports />
      </div>

      {/* Bottom row: Alert Rules + Notification Log */}
      <div className="grid grid-cols-2 gap-6">
        <AlertRules />
        <NotificationLog />
      </div>
    </div></div>
  );
}
