import { useState } from 'react';
import { ChevronDown, ChevronRight, HelpCircle, Zap, Link2, BarChart2, ClipboardList, MessageSquare } from 'lucide-react';

const FAQS = [
  {
    category: 'Getting Started',
    icon: Zap,
    color: 'emerald',
    items: [
      {
        q: 'What does TrueSignal do?',
        a: 'TrueSignal analyzes work order history from your CMMS to calculate a risk score for each asset. It surfaces which assets are most likely to fail soon, recommends optimized PM schedules, and helps you shift from reactive to proactive maintenance.',
      },
      {
        q: 'How do I connect my CMMS?',
        a: 'FaciliWorks integration is coming soon. Once available, go to Settings, enter your FaciliWorks API key, and TrueSignal will sync your assets and work order history automatically.',
      },
      {
        q: 'What pages are in the app?',
        a: 'Overview — fleet-level KPIs and recent activity. Asset Health — per-asset risk rings, Act Now list, and urgency histogram. PM Planner — AI-generated PM schedule recommendations you can accept and push to your CMMS. Settings — platform connection, team management, and alert preferences.',
      },
      {
        q: 'Is my data secure?',
        a: 'Yes. Your CMMS API key is encrypted with AES-256-GCM before storage and never returned to the browser. TrueSignal does not transmit your raw operational data to third parties.',
      },
    ],
  },
  {
    category: 'Asset Health & Risk Scores',
    icon: BarChart2,
    color: 'indigo',
    items: [
      {
        q: 'How is an asset\'s risk score calculated?',
        a: 'The risk score (0–1) is a weighted combination of: (1) work order frequency — assets with more reactive/corrective WOs score higher; (2) recency — recent failures carry more weight; (3) history depth — sparse history is penalized; (4) recent PM credit — a completed PM reduces the score.',
      },
      {
        q: 'What do the risk levels mean?',
        a: 'CRITICAL (≥ 0.75): Immediate action recommended. HIGH (0.50–0.75): Schedule maintenance soon. MEDIUM (0.25–0.50): Monitor and plan next PM. LOW (< 0.25): Asset is healthy — follow standard schedule.',
      },
      {
        q: 'What is the Maintenance Health score on the Overview?',
        a: 'The health score is a fleet-level indicator. It starts at 50, subtracts 3 points per Critical asset and 1 point per High risk asset, and adds up to 5 points for strong PM compliance. Scores below 40 indicate a reactive maintenance culture.',
      },
      {
        q: 'How many data points are needed for an accurate score?',
        a: 'TrueSignal performs best with 6+ months of WO history. Assets with fewer than 3 WOs will have less reliable scores, shown as a lower confidence percentage.',
      },
    ],
  },
  {
    category: 'FaciliWorks Integration',
    icon: Link2,
    color: 'sky',
    items: [
      {
        q: 'When will FaciliWorks integration be available?',
        a: 'FaciliWorks integration is actively in development and will be available soon. You\'ll be notified by email when it\'s ready to connect.',
      },
      {
        q: 'What data will TrueSignal pull from FaciliWorks?',
        a: 'TrueSignal will fetch your asset list and all work orders (corrective and preventive). It uses completion dates, WO types, and asset associations to build the risk model. It will not read or modify any other data.',
      },
      {
        q: 'Why are some assets missing?',
        a: 'TrueSignal only processes assets that have at least one associated work order. Assets with no WO history will not appear in the dashboard.',
      },
      {
        q: 'Will TrueSignal write back to FaciliWorks?',
        a: 'Yes — once connected, accepted PM suggestions in the PM Planner can be pushed directly to FaciliWorks as scheduled work orders with one click.',
      },
    ],
  },
  {
    category: 'PM Planner & Alerts',
    icon: ClipboardList,
    color: 'violet',
    items: [
      {
        q: 'How are PM suggestions generated?',
        a: 'TrueSignal analyzes each asset\'s work order history, reactive work rate after PMs, and mean time between failures (MTBF). If the data suggests a different PM cadence would reduce reactive work, a suggestion is generated with a reason and confidence score.',
      },
      {
        q: 'What does accepting a PM suggestion do?',
        a: 'Accepting marks the suggestion as approved and queues it for generation. Once FaciliWorks is connected, you\'ll be able to push accepted suggestions directly to your CMMS as scheduled PM work orders.',
      },
      {
        q: 'How do alerts work?',
        a: 'Alert thresholds are configured in Settings → Alerts. You can toggle alerts for events like a Critical asset being detected or PM compliance dropping below 70%. Email delivery will activate once email is configured for your account.',
      },
      {
        q: 'Can I reject a suggestion and re-evaluate later?',
        a: 'Yes. Rejected suggestions can be reset to "pending" at any time from the PM Planner detail panel. Suggestions are regenerated on each sync so the data stays current.',
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
    <div className="h-full overflow-y-auto"><div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Help &amp; Documentation</h1>
          <p className="text-sm text-slate-400 mt-0.5">Answers to common questions about TrueSignal</p>
        </div>
        <a
          href="mailto:support@truesignalapp.com"
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
          href="mailto:support@truesignalapp.com"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <MessageSquare className="w-4 h-4" />
          Email Support
        </a>
      </div>
    </div></div>
  );
}
