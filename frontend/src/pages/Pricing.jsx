import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, Zap, Building2, ChevronRight } from 'lucide-react';

const PRO_MONTHLY = 49;
const PRO_ANNUAL  = 41;   // per month, billed $490/yr
const SEAT_PRICE  = 15;

const PRO_FEATURES = [
  '1 facility location',
  '3 seats included',
  `+$${SEAT_PRICE}/seat/mo for additional users`,
  'AI failure predictions (daily)',
  'PM schedule optimization',
  'FaciliWorks integration',
  'KPI intelligence dashboard',
  'Alert rules & email notifications',
  'CSV + PDF report exports',
  'Email support',
];

const ENTERPRISE_FEATURES = [
  'Unlimited locations',
  'Unlimited seats',
  'Everything in Pro',
  'Multi-site fleet overview',
  'Custom CMMS integrations',
  'Dedicated onboarding',
  'SLA & uptime guarantee',
  'Priority support + Slack channel',
  'Custom contract & invoicing',
];

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="36" height="22" viewBox="0 0 44 28" fill="none">
        <defs>
          <linearGradient id="lg-pricing" x1="0" y1="0" x2="44" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
        <polyline points="0,14 8,14 11,14 14,3 17,25 20,14 22,14 44,14"
          stroke="url(#lg-pricing)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="14" cy="3" r="2.5" fill="#34d399" />
      </svg>
      <span className="text-lg font-bold text-white tracking-tight">
        True<span style={{ color: '#34d399' }}>Signal</span>
      </span>
    </div>
  );
}

export default function Pricing() {
  const [annual, setAnnual] = useState(false);
  const navigate = useNavigate();

  const price = annual ? PRO_ANNUAL : PRO_MONTHLY;
  const annualTotal = PRO_ANNUAL * 12;
  const savings = annual ? (PRO_MONTHLY * 12 - annualTotal) : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">

      {/* Nav */}
      <nav className="flex-shrink-0 w-full px-8 py-3.5 flex items-center justify-between border-b border-slate-800/60">
        <Link to="/"><Logo /></Link>
        <div className="flex items-center gap-2">
          <Link to="/login" className="text-sm text-slate-300 hover:text-white px-4 py-1.5 rounded-lg transition-colors">Sign In</Link>
          <Link to="/signup" className="text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors">Start Free Trial</Link>
        </div>
      </nav>

      {/* Header */}
      <div className="text-center pt-16 pb-10 px-6">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium px-3 py-1 rounded-full mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          30-day free trial · No credit card required
        </div>
        <h1 className="text-4xl font-bold text-white mb-3">Simple, transparent pricing</h1>
        <p className="text-slate-400 text-base max-w-lg mx-auto">
          Start free. Upgrade when you're ready. Cancel anytime.
        </p>

        {/* Monthly / Annual toggle */}
        <div className="flex items-center justify-center gap-3 mt-8">
          <span className={`text-sm font-medium ${!annual ? 'text-white' : 'text-slate-500'}`}>Monthly</span>
          <button
            onClick={() => setAnnual(a => !a)}
            className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${annual ? 'bg-indigo-600' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${annual ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
          <span className={`text-sm font-medium ${annual ? 'text-white' : 'text-slate-500'}`}>
            Annual
            <span className="ml-2 text-[10px] font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-1.5 py-0.5 rounded-full">
              2 months free
            </span>
          </span>
        </div>
      </div>

      {/* Plan cards */}
      <div className="flex-1 px-6 pb-16">
        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Pro */}
          <div className="relative bg-slate-900 border-2 border-indigo-500/60 rounded-2xl p-8 flex flex-col shadow-xl shadow-indigo-500/10">
            {/* Most popular badge */}
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span className="bg-indigo-600 text-white text-xs font-semibold px-4 py-1 rounded-full">Most Popular</span>
            </div>

            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-indigo-500/15 border border-indigo-500/25">
                <Zap className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Pro</h2>
                <p className="text-xs text-slate-400">For maintenance teams</p>
              </div>
            </div>

            <div className="mb-2">
              <span className="text-5xl font-bold text-white">${price}</span>
              <span className="text-slate-400 text-sm ml-1">/mo</span>
            </div>
            {annual && (
              <p className="text-xs text-emerald-400 mb-1">Billed ${annualTotal}/yr — save ${savings}</p>
            )}
            <p className="text-xs text-slate-500 mb-8">
              {annual ? `$${annualTotal} billed annually` : 'Billed monthly · cancel anytime'}
            </p>

            <Link
              to="/signup"
              className="w-full text-center bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl text-sm transition-colors shadow-lg shadow-indigo-500/20 mb-8"
            >
              Start 30-day free trial
            </Link>

            <ul className="space-y-3 flex-1">
              {PRO_FEATURES.map(f => (
                <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Enterprise */}
          <div className="bg-slate-900 border border-slate-700/60 rounded-2xl p-8 flex flex-col">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-slate-700/50 border border-slate-600/40">
                <Building2 className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Enterprise</h2>
                <p className="text-xs text-slate-400">For multi-site organizations</p>
              </div>
            </div>

            <div className="mb-2">
              <span className="text-5xl font-bold text-white">Custom</span>
            </div>
            <p className="text-xs text-slate-500 mb-8">Tailored to your fleet size and needs</p>

            <button
              onClick={() => {
                // POST to /billing/contact-enterprise — fire and forget
                fetch('/billing/contact-enterprise', { method: 'POST' }).catch(() => {});
                navigate('/signup?enterprise=1');
              }}
              className="w-full text-center border border-slate-600 hover:border-slate-400 text-slate-200 hover:text-white font-semibold py-3 rounded-xl text-sm transition-colors mb-8"
            >
              Contact sales
            </button>

            <ul className="space-y-3 flex-1">
              {ENTERPRISE_FEATURES.map(f => (
                <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* FAQ-style reassurances */}
        <div className="max-w-4xl mx-auto mt-14 grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { q: 'No credit card needed', a: 'Start your 30-day trial instantly. We\'ll only ask for payment details when you\'re ready to upgrade.' },
            { q: 'Cancel anytime', a: 'No long-term contracts on Pro. Cancel from your account settings — your data is always exportable.' },
            { q: 'Have a promo code?', a: 'Enter it at signup or in your account settings to extend your trial or unlock free Pro access.' },
          ].map(({ q, a }) => (
            <div key={q} className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-5">
              <p className="text-sm font-semibold text-white mb-1.5">{q}</p>
              <p className="text-xs text-slate-400 leading-relaxed">{a}</p>
            </div>
          ))}
        </div>

        {/* CTA strip */}
        <div className="max-w-4xl mx-auto mt-10 text-center">
          <p className="text-slate-500 text-sm">
            Questions? <a href="mailto:support@truesignalapp.com" className="text-indigo-400 hover:text-indigo-300">Email us</a> or <Link to="/signup" className="text-indigo-400 hover:text-indigo-300">start your free trial</Link> — no card required.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 px-8 py-3 flex items-center justify-between">
        <Logo />
        <p className="text-xs text-slate-600">© 2026 TrueSignal. All rights reserved.</p>
      </footer>

    </div>
  );
}
