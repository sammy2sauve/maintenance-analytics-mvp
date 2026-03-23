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
    desc: 'Stop over-maintaining assets that don\'t need it. Optimize PM frequencies and quantify the savings.',
  },
  {
    Icon: BarChart3,
    title: 'KPI Intelligence',
    desc: 'Your CMMS data has distortions — rushed completions, duplicate work orders. We surface the real numbers.',
  },
];

const STATS = [
  { value: 'Days early', label: 'Know about failures before they happen' },
  { value: 'Real savings', label: 'Quantified PM optimization opportunities' },
  { value: 'Your data', label: 'Works from your existing CMMS history' },
];

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="44" height="28" viewBox="0 0 44 28" fill="none">
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
      <span className="text-xl font-bold text-white tracking-tight">
        True<span style={{ color: '#34d399' }}>Signal</span>
      </span>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">

      {/* Nav */}
      <nav className="w-full px-8 py-4 flex items-center justify-between border-b border-slate-800/60">
        <Logo />
        <div className="flex items-center gap-3">
          <Link to="/login"
            className="text-sm text-slate-300 hover:text-white px-4 py-2 rounded-lg transition-colors">
            Sign In
          </Link>
          <Link to="/signup"
            className="text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg transition-colors">
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center py-20">

        {/* Badge */}
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium px-3 py-1 rounded-full mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Predictive Maintenance Intelligence
        </div>

        <h1 className="text-5xl font-bold text-white leading-tight max-w-2xl mb-4">
          Stop reacting.<br />
          <span style={{ color: '#34d399' }}>Start predicting.</span>
        </h1>

        <p className="text-lg text-slate-400 max-w-xl mb-10 leading-relaxed">
          TrueSignal connects to your CMMS, analyzes work order patterns, and tells you
          which assets are about to fail — before they do.
        </p>

        <div className="flex items-center gap-4">
          <Link to="/signup"
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 py-3 rounded-xl text-sm transition-colors shadow-lg shadow-indigo-500/20">
            Start Free Trial
          </Link>
          <Link to="/login"
            className="text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 px-6 py-3 rounded-xl text-sm transition-colors">
            Sign In
          </Link>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-12 mt-16 pt-12 border-t border-slate-800/60">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <p className="text-2xl font-bold text-white">{s.value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Features */}
      <section className="px-8 pb-20 max-w-4xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURES.map(({ Icon, title, desc }) => (
            <div key={title}
              className="bg-slate-900 border border-slate-700/50 rounded-2xl p-6 hover:border-indigo-500/30 transition-colors">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 w-fit mb-4">
                <Icon className="w-5 h-5 text-indigo-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 px-8 py-4 flex items-center justify-between">
        <Logo />
        <p className="text-xs text-slate-600">© 2026 TrueSignal. All rights reserved.</p>
      </footer>
    </div>
  );
}
