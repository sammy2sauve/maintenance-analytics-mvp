import { useState } from 'react';
import { ChevronDown, ChevronRight, HelpCircle, Zap, Link2, BarChart2, FileText, MessageSquare } from 'lucide-react';

const FAQS = [
  {
    category: 'Getting Started',
    icon: Zap,
    color: 'emerald',
    items: [
      {
        q: 'What does TrueSignal do?',
        a: 'TrueSignal analyzes work order history from your CMMS to calculate a risk score for each asset. It surfaces which assets are most likely to fail soon, and recommends optimized PM schedules to reduce unplanned downtime and maintenance costs.',
      },
      {
        q: 'How do I connect my CMMS?',
        a: 'Go to Settings and enter your MaintainX API key. TrueSignal will sync your assets and work order history automatically. After the initial sync, data refreshes whenever you click "Sync" in the navigation bar.',
      },
      {
        q: 'How often should I sync?',
        a: 'For most facilities, a daily sync is sufficient. The Sync button in the top nav triggers an immediate sync. A scheduled automatic daily sync is on the roadmap.',
      },
      {
        q: 'Is my data secure?',
        a: 'Yes. Your CMMS API key is encrypted with AES-256-GCM before storage. TrueSignal never transmits your raw operational data outside your environment.',
      },
    ],
  },
  {
    category: 'Understanding Risk Scores',
    icon: BarChart2,
    color: 'indigo',
    items: [
      {
        q: 'How is an asset\'s risk score calculated?',
        a: 'The risk score (0–1) is a weighted combination of four factors: (1) work order frequency — assets with more reactive/corrective WOs score higher; (2) recency — recent failures carry more weight than older ones; (3) work order age — older assets with sparse history are penalized; (4) recent maintenance credit — assets with recent completed PMs receive a score reduction.',
      },
      {
        q: 'What do the risk levels mean?',
        a: 'CRITICAL (≥ 0.75): Immediate action recommended — high likelihood of imminent failure. HIGH (0.50–0.75): Schedule maintenance soon. MEDIUM (0.25–0.50): Monitor closely and plan next PM. LOW (< 0.25): Asset is healthy — follow standard PM schedule.',
      },
      {
        q: 'Why does an asset with recent PM work show as CRITICAL?',
        a: 'If an asset has a very high corrective WO frequency or recent failures, the maintenance credit may not fully offset the underlying risk. This is intentional — a single PM after many failures does not fully restore an asset to low risk. Review the asset\'s full WO history for context.',
      },
      {
        q: 'How many data points are needed for an accurate score?',
        a: 'TrueSignal performs best with 6+ months of WO history. Assets with fewer than 3 WOs will have less reliable scores, indicated by a lower confidence level.',
      },
    ],
  },
  {
    category: 'MaintainX Integration',
    icon: Link2,
    color: 'sky',
    items: [
      {
        q: 'Which MaintainX plan do I need?',
        a: 'TrueSignal requires API access, which is available on MaintainX Business and Enterprise plans. The API key can be found in your MaintainX account under Settings → API.',
      },
      {
        q: 'What data does TrueSignal pull from MaintainX?',
        a: 'TrueSignal fetches your asset list and all work orders (corrective, preventive, and reactive). It uses work order completion dates, types, and asset associations to build the risk model. It does not read or write any other data.',
      },
      {
        q: 'Why are some assets missing after sync?',
        a: 'TrueSignal only processes assets that have at least one associated work order. Assets with no WO history will not appear in the dashboard. Create a baseline WO in MaintainX for those assets and re-sync.',
      },
      {
        q: 'How are PM suggestion statuses tracked?',
        a: 'When a PM suggestion is created in TrueSignal and a corresponding WO is completed in MaintainX, the next sync marks the suggestion as "Implemented." This is automatic — no manual status updates are needed.',
      },
    ],
  },
  {
    category: 'Reports & Alerts',
    icon: FileText,
    color: 'violet',
    items: [
      {
        q: 'What can I include in a report?',
        a: 'Reports can include: Overview Summary, Asset Health Breakdown, Critical & High Risk asset lists, PM Recommendations, Cost Savings Analysis, and AI Insights. Select the sections you need in the Report Builder.',
      },
      {
        q: 'Can I schedule automated reports?',
        a: 'Yes. Go to Reports & Alerts → Scheduled Reports to set up daily, weekly, or monthly automated report deliveries to any email address.',
      },
      {
        q: 'How do alert rules work?',
        a: 'Alert rules define conditions that trigger email notifications — for example, "notify me when any asset reaches CRITICAL risk." Alerts fire after each sync if the condition is newly met.',
      },
      {
        q: 'What report formats are available?',
        a: 'PDF (formatted for sharing), CSV (raw data for spreadsheets), and Excel (with charts). Report generation and export are coming in the next release.',
      },
    ],
  },
];

const colorMap = {
  emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: 'text-emerald-400', pill: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  indigo:  { bg: 'bg-indigo-500/10',  border: 'border-indigo-500/20',  icon: 'text-indigo-400',  pill: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
  sky:     { bg: 'bg-sky-500/10',     border: 'border-sky-500/20',     icon: 'text-sky-400',     pill: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  violet:  { bg: 'bg-violet-500/10',  border: 'border-violet-500/20',  icon: 'text-violet-400',  pill: 'bg-violet-500/10 text-violet-400 border-violet-500/20' },
};

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-slate-700/50 last:border-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-start justify-between gap-3 py-4 text-left group"
      >
        <span className={`text-sm font-medium transition-colors ${open ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>
          {q}
        </span>
        {open
          ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          : <ChevronRight className="w-4 h-4 text-slate-500 shrink-0 mt-0.5 group-hover:text-slate-400" />
        }
      </button>
      {open && (
        <p className="text-sm text-slate-400 leading-relaxed pb-4">
          {a}
        </p>
      )}
    </div>
  );
}

function FAQCategory({ category, icon: Icon, color, items }) {
  const c = colorMap[color];
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className={`p-2 rounded-lg ${c.bg} border ${c.border}`}>
          <Icon className={`w-5 h-5 ${c.icon}`} />
        </div>
        <h2 className="text-base font-semibold text-white">{category}</h2>
        <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full border ${c.pill}`}>
          {items.length} topics
        </span>
      </div>
      <div>
        {items.map((item, i) => (
          <FAQItem key={i} q={item.q} a={item.a} />
        ))}
      </div>
    </div>
  );
}

export default function Help() {
  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Help &amp; Documentation</h1>
          <p className="text-sm text-slate-400 mt-0.5">Answers to common questions about TrueSignal</p>
        </div>
        <a
          href="mailto:support@truesignal.io"
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
        >
          <MessageSquare className="w-4 h-4" />
          Contact Support
        </a>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-4 gap-3">
        {FAQS.map(({ category, icon: Icon, color }) => {
          const c = colorMap[color];
          return (
            <button
              key={category}
              onClick={() => document.getElementById(category)?.scrollIntoView({ behavior: 'smooth' })}
              className="flex items-center gap-2.5 p-3.5 bg-slate-800/60 border border-slate-700/50 rounded-xl hover:border-slate-600 transition-colors text-left group"
            >
              <div className={`p-1.5 rounded-lg ${c.bg} border ${c.border} shrink-0`}>
                <Icon className={`w-4 h-4 ${c.icon}`} />
              </div>
              <span className="text-xs font-medium text-slate-400 group-hover:text-slate-200 transition-colors leading-snug">
                {category}
              </span>
            </button>
          );
        })}
      </div>

      {/* FAQ sections */}
      <div className="space-y-4">
        {FAQS.map(section => (
          <div key={section.category} id={section.category}>
            <FAQCategory {...section} />
          </div>
        ))}
      </div>

      {/* Footer CTA */}
      <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-6 text-center">
        <HelpCircle className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-white mb-1">Can't find what you're looking for?</h3>
        <p className="text-sm text-slate-400 mb-4">
          Our support team is available to help with setup, integration questions, and feature requests.
        </p>
        <a
          href="mailto:support@truesignal.io"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <MessageSquare className="w-4 h-4" />
          Email Support
        </a>
      </div>
    </div>
  );
}
