import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Zap, Wrench, BarChart3, ChevronRight } from 'lucide-react';

// ─── Slide: Asset Health ──────────────────────────────────────────────────────
// Matches: toolbar + 4 glowing SVG rings + main list + Act Now sidebar

function SlideAssetHealth() {
  const rings = [
    { level: 'CRITICAL', count: 2,  total: 29, color: '#f87171' },
    { level: 'HIGH',     count: 9,  total: 29, color: '#fb923c' },
    { level: 'MEDIUM',   count: 7,  total: 29, color: '#fbbf24' },
    { level: 'LOW',      count: 11, total: 29, color: '#34d399' },
  ];
  const assets = [
    { id: 'MMC-CHIL-001', risk: 'CRITICAL', prob: 91, days: 6  },
    { id: 'MMC-AHU-003',  risk: 'CRITICAL', prob: 80, days: 11 },
    { id: 'MMC-BOIL-001', risk: 'HIGH',     prob: 72, days: 18 },
    { id: 'MMC-COMP-002', risk: 'HIGH',     prob: 68, days: 22 },
    { id: 'MMC-CTW-001',  risk: 'HIGH',     prob: 65, days: 29 },
    { id: 'MMC-CHWP-001', risk: 'MEDIUM',   prob: 48, days: 45 },
    { id: 'MMC-VFD-003',  risk: 'MEDIUM',   prob: 41, days: 52 },
  ];
  const riskColor = { CRITICAL: '#f87171', HIGH: '#fb923c', MEDIUM: '#fbbf24', LOW: '#34d399' };
  const riskBg = { CRITICAL: 'bg-red-500/10 text-red-400', HIGH: 'bg-orange-500/10 text-orange-400', MEDIUM: 'bg-amber-500/10 text-amber-400', LOW: 'bg-emerald-500/10 text-emerald-400' };

  const actNow = assets.slice(0, 4);

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-shrink-0">
        <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
          Asset Health <span className="text-slate-600 normal-case">(29 assets)</span>
        </p>
        <div className="bg-slate-800 border border-slate-700 rounded px-2 py-0.5 text-[8px] text-slate-500">Search asset…</div>
      </div>

      {/* 4 risk rings */}
      <div className="grid grid-cols-4 gap-2 flex-shrink-0">
        {rings.map(({ level, count, total, color }) => {
          const pct = count / total;
          const r = 28, cx = 36, cy = 36, circ = 2 * Math.PI * r;
          const glowId = `glow-${level}-lp`;
          return (
            <div key={level} className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-2 flex flex-col items-center">
              <svg viewBox="0 0 72 72" className="w-full" style={{ maxWidth: 60 }}>
                <defs>
                  <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="2" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>
                <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth="6" />
                {count > 0 && (
                  <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="6"
                    strokeDasharray={`${pct * circ} ${circ}`} strokeLinecap="round"
                    transform={`rotate(-90 ${cx} ${cy})`} filter={`url(#${glowId})`} />
                )}
                <text x={cx} y={cx - 4} textAnchor="middle" fill="white" fontSize="14" fontWeight="700">{count}</text>
                <text x={cx} y={cx + 9} textAnchor="middle" fill={color} fontSize="6" fontWeight="500">{Math.round(pct * 100)}%</text>
              </svg>
              <p className="text-[8px] font-bold mt-0.5" style={{ color }}>{level}</p>
            </div>
          );
        })}
      </div>

      {/* Two-col: asset list + Act Now */}
      <div className="flex gap-2 flex-1 min-h-0">
        {/* Asset list */}
        <div className="flex-1 bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="grid grid-cols-4 px-3 py-1.5 border-b border-slate-700/40">
            {['Asset ID', 'Risk', 'Prob.', 'Days'].map(h => (
              <span key={h} className="text-[8px] text-slate-500 font-semibold uppercase">{h}</span>
            ))}
          </div>
          {assets.map(a => (
            <div key={a.id} className="grid grid-cols-4 px-3 py-1.5 border-b border-slate-700/20 last:border-0 items-center">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: riskColor[a.risk] }} />
                <span className="text-[9px] text-slate-300 font-medium truncate">{a.id}</span>
              </div>
              <span className={`text-[8px] font-semibold px-1 py-0.5 rounded-full w-fit ${riskBg[a.risk]}`}>{a.risk}</span>
              <span className="text-[9px] text-slate-300 font-mono">{a.prob}%</span>
              <span className="text-[9px] text-slate-400">{a.days}d</span>
            </div>
          ))}
        </div>

        {/* Act Now sidebar */}
        <div className="w-28 flex-shrink-0 bg-slate-900/80 border border-slate-700/50 rounded-xl p-2 flex flex-col">
          <p className="text-[9px] font-semibold text-white mb-2">Act Now</p>
          <div className="space-y-1.5 flex-1">
            {actNow.map(a => (
              <div key={a.id} className="bg-slate-800/60 rounded-lg px-2 py-1.5 border border-slate-700/40">
                <p className="text-[8px] font-semibold truncate" style={{ color: riskColor[a.risk] }}>{a.id}</p>
                <p className="text-[8px] text-slate-500">{a.days}d · {a.prob}%</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Slide: PM Planner ────────────────────────────────────────────────────────
// Matches: 3 stat cards + filter tabs + two-panel (list | detail)

function SlidePMPlanner() {
  const suggestions = [
    { asset: 'MMC-CHWP-001', name: 'Chilled Water Pump #1', from: 90,  to: 60,  status: 'pending',     conf: 88 },
    { asset: 'MMC-VFD-003',  name: 'VFD-003',               from: 60,  to: 90,  status: 'implemented', conf: 79 },
    { asset: 'MMC-HEX-001',  name: 'Heat Exchanger #1',     from: 180, to: 120, status: 'pending',     conf: 83 },
    { asset: 'MMC-EXH-002',  name: 'Exhaust Fan #2',        from: 30,  to: 60,  status: 'implemented', conf: 91 },
    { asset: 'MMC-BOIL-002', name: 'Boiler #2',             from: 60,  to: 45,  status: 'rejected',    conf: 62 },
  ];
  const STATUS_STYLES = {
    pending:     { bg: 'bg-amber-500/10',  text: 'text-amber-400',  border: 'border-amber-500/20'  },
    implemented: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20' },
    rejected:    { bg: 'bg-red-500/10',    text: 'text-red-400',    border: 'border-red-500/20'    },
  };

  // Selected item (detail panel) — show the first one
  const sel = suggestions[0];

  return (
    <div className="flex flex-col gap-2 h-full">
      <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">PM Planner</p>

      {/* 3 stat cards — dark style matching PMPlanner StatCard */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        {[['Pending review', 11, 'text-amber-400'], ['Implemented', 18, 'text-indigo-400'], ['Rejected', 3, 'text-slate-400']].map(([l, v, c]) => (
          <div key={l} className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-2.5">
            <p className="text-[8px] text-slate-500 uppercase tracking-wide mb-0.5">{l}</p>
            <p className={`text-xl font-bold ${c}`}>{v}</p>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1.5 flex-shrink-0">
        {['All (32)', 'pending', 'implemented', 'rejected'].map((f, i) => (
          <span key={f} className={`px-2.5 py-0.5 rounded-full text-[8px] font-medium capitalize ${i === 0 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
            {f}
          </span>
        ))}
      </div>

      {/* Two-panel */}
      <div className="flex gap-2 flex-1 min-h-0">
        {/* List */}
        <div className="flex-1 space-y-1.5 overflow-hidden">
          {suggestions.map((s, i) => {
            const ss = STATUS_STYLES[s.status];
            const tighter = s.to < s.from;
            return (
              <div key={s.asset} className={`bg-slate-900/80 border rounded-xl px-2.5 py-2 ${i === 0 ? 'border-indigo-500/50 bg-indigo-950/30' : 'border-slate-700/50'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-semibold text-white truncate">{s.asset}</span>
                  <span className={`text-[7px] font-medium px-1.5 py-0.5 rounded-full border capitalize ${ss.bg} ${ss.text} ${ss.border}`}>{s.status}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[8px] text-slate-400 font-mono">{s.from}d</span>
                  <ChevronRight className={`w-2 h-2 ${tighter ? 'text-emerald-400' : 'text-amber-400'}`} />
                  <span className={`text-[8px] font-mono font-semibold ${tighter ? 'text-emerald-400' : 'text-amber-400'}`}>{s.to}d</span>
                  <span className="text-[7px] text-slate-600 ml-auto">{s.conf}% conf</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detail panel */}
        <div className="w-32 flex-shrink-0 bg-slate-900/80 border border-slate-700/50 rounded-xl p-2.5 flex flex-col gap-2">
          <div>
            <p className="text-[9px] font-semibold text-white">{sel.asset}</p>
            <span className="text-[7px] font-medium px-1.5 py-0.5 rounded-full border bg-amber-500/10 text-amber-400 border-amber-500/20">pending</span>
          </div>
          <div className="bg-slate-800/60 rounded-lg p-2 text-center">
            <p className="text-[8px] text-slate-500 mb-1">PM Frequency</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-sm font-bold text-slate-300">{sel.from}d</span>
              <ChevronRight className="w-2.5 h-2.5 text-indigo-400" />
              <span className="text-sm font-bold text-emerald-400">{sel.to}d</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-1">
            <div className="bg-slate-800/40 rounded p-1.5 text-center">
              <p className="text-[9px] font-semibold text-white">88%</p>
              <p className="text-[7px] text-slate-500">Confidence</p>
            </div>
            <div className="bg-slate-800/40 rounded p-1.5 text-center">
              <p className="text-[9px] font-semibold text-emerald-400">−12%</p>
              <p className="text-[7px] text-slate-500">Risk Δ</p>
            </div>
          </div>
          <button className="w-full flex items-center justify-center gap-1 px-2 py-1.5 bg-indigo-600 text-white text-[8px] font-medium rounded-lg mt-auto">
            <Zap className="w-2 h-2" />
            Implement in FaciliWorks
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Rotating preview wrapper ─────────────────────────────────────────────────

const SLIDES = [
  { id: 'assets', label: 'Asset Health', component: SlideAssetHealth },
  { id: 'pm',     label: 'PM Planner',   component: SlidePMPlanner   },
];

function AppPreview() {
  const [active, setActive] = useState(0);
  const [fading, setFading] = useState(false);

  const goTo = (idx) => {
    if (idx === active) return;
    setFading(true);
    setTimeout(() => { setActive(idx); setFading(false); }, 180);
  };

  useEffect(() => {
    const t = setInterval(() => {
      setFading(true);
      setTimeout(() => { setActive(prev => (prev + 1) % SLIDES.length); setFading(false); }, 180);
    }, 5000);
    return () => clearInterval(t);
  }, []);

  const Slide = SLIDES[active].component;

  return (
    <div className="w-full h-full flex flex-col">
      {/* Browser chrome */}
      <div className="bg-slate-800 rounded-t-xl border border-slate-700/60 border-b-0 px-3 py-2 flex items-center gap-2 flex-shrink-0">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <div className="flex gap-1 ml-2">
          {SLIDES.map((s, i) => (
            <button key={s.id} onClick={() => goTo(i)}
              className={`text-[9px] px-2.5 py-0.5 rounded-md font-medium transition-colors ${active === i ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'}`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* App frame */}
      <div className="flex-1 bg-slate-950 border border-slate-700/60 border-t-0 rounded-b-xl px-3 py-3 overflow-hidden relative">
        {/* Subtle grid */}
        <div className="absolute inset-0 opacity-[0.025]"
          style={{ backgroundImage: 'linear-gradient(#6366f1 1px,transparent 1px),linear-gradient(90deg,#6366f1 1px,transparent 1px)', backgroundSize: '24px 24px' }} />
        {/* Slide content — slight blur to tease without fully exposing */}
        <div className="h-full relative transition-opacity duration-200" style={{ opacity: fading ? 0 : 1, filter: 'blur(0.6px)' }}>
          <Slide />
        </div>
        {/* Bottom fade — obscures lower detail, feels intentional */}
        <div className="absolute bottom-0 left-0 right-0 h-24 rounded-b-xl pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, transparent, #0f172a)' }} />
      </div>

      {/* Dot indicators */}
      <div className="flex items-center justify-center gap-2 mt-2">
        {SLIDES.map((_, i) => (
          <button key={i} onClick={() => goTo(i)}
            className={`h-1.5 rounded-full transition-all duration-300 ${active === i ? 'bg-indigo-400 w-4' : 'bg-slate-600 w-1.5 hover:bg-slate-500'}`} />
        ))}
      </div>
    </div>
  );
}

// ─── Landing page ─────────────────────────────────────────────────────────────

const FEATURES = [
  { Icon: Zap,      title: 'Failure Prediction', desc: 'Know which assets are about to fail before they do. Risk scores updated daily from your work order history.' },
  { Icon: Wrench,   title: 'PM Optimization',    desc: 'Stop over-maintaining assets that don\'t need it. Optimize frequencies and quantify the savings.' },
  { Icon: BarChart3,title: 'KPI Intelligence',   desc: 'Surface the real numbers from your CMMS data — no more rushed completions distorting your metrics.' },
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
          <Link to="/login" className="text-sm text-slate-300 hover:text-white px-4 py-1.5 rounded-lg transition-colors">Sign In</Link>
          <Link to="/signup" className="text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors">Get Started</Link>
        </div>
      </nav>

      {/* Hero — two-column */}
      <main className="flex-1 min-h-0 flex items-center gap-10 px-10 py-4">

        {/* Left: copy */}
        <div className="flex-shrink-0 w-[360px] flex flex-col">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium px-3 py-1 rounded-full mb-5 w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Predictive Maintenance Intelligence
          </div>

          <h1 className="text-4xl font-bold text-white leading-tight mb-3">
            Stop reacting.<br />
            <span style={{ color: '#34d399' }}>Start predicting.</span>
          </h1>

          <p className="text-sm text-slate-400 mb-7 leading-relaxed">
            TrueSignal connects to your CMMS, analyzes work order patterns, and tells you
            which assets are about to fail — before they do.
          </p>

          <div className="flex items-center gap-3 mb-8">
            <Link to="/signup" className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors shadow-lg shadow-indigo-500/20">
              Start Free Trial
            </Link>
            <Link to="/login" className="text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 px-6 py-2.5 rounded-xl text-sm transition-colors">
              Sign In
            </Link>
          </div>

          <div className="space-y-3">
            {FEATURES.map(({ Icon, title, desc }) => (
              <div key={title} className="flex items-start gap-3">
                <div className="p-1.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 flex-shrink-0 mt-0.5">
                  <Icon className="w-3 h-3 text-indigo-400" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-white">{title}</p>
                  <p className="text-[11px] text-slate-500 leading-snug">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: rotating app preview */}
        <div className="flex-1 min-w-0 h-full py-1">
          <AppPreview />
        </div>

      </main>

      {/* Bottom strip */}
      <div className="flex-shrink-0 border-t border-slate-800/60 px-8 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-500 font-medium">Integrates with</span>
          {CMMS.map((c, i) => (
            <span key={c.name} className="flex items-center gap-3">
              <span className={`text-[11px] font-semibold ${c.color}`}>{c.name}</span>
              {i < CMMS.length - 1 && <span className="text-slate-700">·</span>}
            </span>
          ))}
          <span className="text-slate-700">·</span>
          <span className="text-[11px] text-slate-600 italic">more coming soon</span>
        </div>
        <p className="text-[11px] text-slate-600">© 2026 TrueSignal. All rights reserved.</p>
      </div>

    </div>
  );
}
