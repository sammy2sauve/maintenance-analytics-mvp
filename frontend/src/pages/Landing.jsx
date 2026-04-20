import { Link } from 'react-router-dom';
import { Zap, Wrench, BarChart3 } from 'lucide-react';

const FEATURES = [
  {
    Icon: Zap,
    title: 'Failure Prediction',
    desc: 'Know which assets are about to fail before they do. Risk scores updated daily from your work order history.',
  },
  {
    Icon: Wrench,
    title: 'PM Optimization',
    desc: 'Stop over-maintaining assets that don\'t need it. Optimize frequencies and quantify the savings.',
  },
  {
    Icon: BarChart3,
    title: 'KPI Intelligence',
    desc: 'Surface the real numbers from your CMMS data — no more rushed completions distorting your metrics.',
  },
];

const PROOF = [
  { value: 'Days early', label: 'Failure warnings' },
  { value: 'Real savings', label: 'PM optimization' },
  { value: 'Your CMMS', label: 'No new software' },
];

const CMMS = [
  { name: 'FaciliWorks', color: 'text-indigo-300' },
  { name: 'MaintainX',   color: 'text-emerald-300' },
  { name: 'Limble',      color: 'text-slate-400' },
  { name: 'UpKeep',      color: 'text-slate-400' },
];

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="40" height="25" viewBox="0 0 44 28" fill="none">
        <defs>
          <linearGradient id="lg-land" x1="0" y1="0" x2="44" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
          <filter id="glow-land" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <polyline points="0,14 8,14 11,14 14,3 17,25 20,14 22,14 44,14"
          stroke="url(#lg-land)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          fill="none" filter="url(#glow-land)" />
        <circle cx="14" cy="3" r="2.5" fill="#34d399" filter="url(#glow-land)" />
      </svg>
      <span className="text-lg font-bold text-white tracking-tight">
        True<span style={{ color: '#34d399' }}>Signal</span>
      </span>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="h-screen bg-slate-950 text-white flex flex-col overflow-hidden">

      {/* Nav */}
      <nav className="flex-shrink-0 w-full px-8 py-3.5 flex items-center justify-between border-b border-slate-800/60">
        <Logo />
        <div className="flex items-center gap-2">
          <Link to="/login"
            className="text-sm text-slate-300 hover:text-white px-4 py-1.5 rounded-lg transition-colors">
            Sign In
          </Link>
          <Link to="/signup"
            className="text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center min-h-0">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium px-3 py-1 rounded-full mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Predictive Maintenance Intelligence
        </div>

        <h1 className="text-4xl md:text-5xl font-bold text-white leading-tight max-w-2xl mb-3">
          Stop reacting.<br />
          <span style={{ color: '#34d399' }}>Start predicting.</span>
        </h1>

        <p className="text-base text-slate-400 max-w-lg mb-7 leading-relaxed">
          TrueSignal connects to your CMMS, analyzes work order patterns, and tells you
          which assets are about to fail — before they do.
        </p>

        <div className="flex items-center gap-3">
          <Link to="/signup"
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors shadow-lg shadow-indigo-500/20">
            Start Free Trial
          </Link>
          <Link to="/login"
            className="text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 px-6 py-2.5 rounded-xl text-sm transition-colors">
            Sign In
          </Link>
        </div>
      </main>

      {/* Proof strip */}
      <div className="flex-shrink-0 border-t border-slate-800/60 px-8 py-3">
        <div className="flex items-center justify-center gap-12">
          {PROOF.map(p => (
            <div key={p.value} className="text-center">
              <p className="text-sm font-bold text-white">{p.value}</p>
              <p className="text-[11px] text-slate-500">{p.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Feature cards */}
      <section className="flex-shrink-0 px-8 py-4 border-t border-slate-800/40">
        <div className="grid grid-cols-3 gap-4 max-w-4xl mx-auto">
          {FEATURES.map(({ Icon, title, desc }) => (
            <div key={title}
              className="bg-slate-900 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/30 transition-colors">
              <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 w-fit mb-3">
                <Icon className="w-4 h-4 text-indigo-400" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CMMS integrations strip — new section */}
      <div className="flex-shrink-0 border-t border-slate-800/40 px-8 py-3 bg-slate-900/40">
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <span className="text-xs text-slate-500 font-medium mr-1">Integrates with</span>
          {CMMS.map((c, i) => (
            <span key={c.name} className="flex items-center gap-3">
              <span className={`text-xs font-semibold ${c.color}`}>{c.name}</span>
              {i < CMMS.length - 1 && <span className="text-slate-700">·</span>}
            </span>
          ))}
          <span className="text-slate-700">·</span>
          <span className="text-xs text-slate-600 italic">more coming soon</span>
        </div>
      </div>

      {/* Footer */}
      <footer className="flex-shrink-0 border-t border-slate-800/60 px-8 py-3 flex items-center justify-between">
        <Logo />
        <p className="text-xs text-slate-600">© 2026 TrueSignal. All rights reserved.</p>
      </footer>
    </div>
  );
}
