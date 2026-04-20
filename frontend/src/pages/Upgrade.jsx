import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Zap, Building2, Tag, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const PRO_MONTHLY = 49;
const PRO_ANNUAL  = 41;
const SEAT_PRICE  = 15;

const PRO_FEATURES = [
  '1 facility location',
  '3 seats included',
  `+$${SEAT_PRICE}/seat/mo for additional users`,
  'AI failure predictions (daily)',
  'PM schedule optimization',
  'FaciliWorks integration',
  'KPI dashboard + insights',
  'Alert rules & email notifications',
  'CSV + PDF exports',
  'Email support',
];

export default function Upgrade() {
  const { trialDaysLeft, trialExpired, plan, refreshLocation } = useAuth();
  const [annual, setAnnual] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoResult, setPromoResult] = useState(null); // { success, message }
  const [contactSent, setContactSent] = useState(false);

  const price = annual ? PRO_ANNUAL : PRO_MONTHLY;

  const applyPromo = async () => {
    if (!promoCode.trim()) return;
    setPromoLoading(true);
    setPromoResult(null);
    try {
      const res = await api.post('/billing/apply-promo', { code: promoCode.trim() });
      setPromoResult({ success: true, message: res.data.message });
      await refreshLocation();
    } catch (err) {
      setPromoResult({ success: false, message: err.response?.data?.detail || 'Invalid promo code.' });
    } finally {
      setPromoLoading(false);
    }
  };

  const contactEnterprise = async () => {
    try {
      await api.post('/billing/contact-enterprise');
    } catch { /* ignore */ }
    setContactSent(true);
  };

  const isPro = plan === 'pro';

  return (
    <div className="w-full h-full overflow-y-auto px-6 py-8">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">
            {isPro ? 'Your Plan' : 'Upgrade to Pro'}
          </h1>
          {!isPro && trialExpired && (
            <div className="flex items-center gap-2 mt-3 p-3 bg-red-900/30 border border-red-500/30 rounded-xl">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-300">Your trial has ended. Upgrade to continue using TrueSignal.</p>
            </div>
          )}
          {!isPro && !trialExpired && trialDaysLeft !== null && (
            <p className="text-sm text-slate-400 mt-1">
              <span className="text-indigo-300 font-medium">{trialDaysLeft} days</span> left in your free trial.
            </p>
          )}
          {isPro && (
            <p className="text-sm text-slate-400 mt-1">You're on the Pro plan. Manage your subscription below.</p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">

          {/* Pro card */}
          <div className="bg-slate-900 border-2 border-indigo-500/50 rounded-2xl p-6 flex flex-col shadow-lg shadow-indigo-500/10">
            <div className="flex items-center gap-3 mb-5">
              <div className="p-2 rounded-lg bg-indigo-500/15 border border-indigo-500/25">
                <Zap className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Pro</h2>
                <p className="text-xs text-slate-400">For maintenance teams</p>
              </div>
              {isPro && <span className="ml-auto text-xs bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 px-2 py-0.5 rounded-full font-medium">Current plan</span>}
            </div>

            {/* Billing toggle */}
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-medium ${!annual ? 'text-white' : 'text-slate-500'}`}>Monthly</span>
              <button onClick={() => setAnnual(a => !a)}
                className={`relative w-10 h-5 rounded-full transition-colors ${annual ? 'bg-indigo-600' : 'bg-slate-700'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${annual ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
              <span className={`text-xs font-medium ${annual ? 'text-white' : 'text-slate-500'}`}>
                Annual <span className="text-emerald-400">(2 months free)</span>
              </span>
            </div>

            <div className="mb-1">
              <span className="text-4xl font-bold text-white">${price}</span>
              <span className="text-slate-400 text-sm ml-1">/mo</span>
            </div>
            {annual && <p className="text-xs text-emerald-400 mb-4">Billed ${PRO_ANNUAL * 12}/yr</p>}
            {!annual && <p className="text-xs text-slate-500 mb-4">Billed monthly</p>}

            {!isPro ? (
              <button
                onClick={() => {/* Stripe Checkout — wired up tonight */}}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors shadow-lg shadow-indigo-500/20 mb-5"
              >
                Upgrade to Pro — ${price}/mo
              </button>
            ) : (
              <button
                onClick={() => {/* Stripe customer portal */}}
                className="w-full border border-slate-600 hover:border-slate-400 text-slate-300 hover:text-white font-medium py-2.5 rounded-xl text-sm transition-colors mb-5"
              >
                Manage subscription
              </button>
            )}

            <ul className="space-y-2.5">
              {PRO_FEATURES.map(f => (
                <li key={f} className="flex items-start gap-2 text-xs text-slate-300">
                  <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Enterprise card */}
          <div className="bg-slate-900 border border-slate-700/60 rounded-2xl p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-5">
              <div className="p-2 rounded-lg bg-slate-700/50 border border-slate-600/40">
                <Building2 className="w-4 h-4 text-slate-300" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Enterprise</h2>
                <p className="text-xs text-slate-400">Multi-site organizations</p>
              </div>
            </div>

            <p className="text-4xl font-bold text-white mb-1">Custom</p>
            <p className="text-xs text-slate-500 mb-4">Tailored pricing · custom contract</p>

            {contactSent ? (
              <div className="w-full text-center bg-emerald-900/30 border border-emerald-500/30 text-emerald-400 text-sm font-medium py-2.5 rounded-xl mb-5">
                Thanks! We'll be in touch within 1 business day.
              </div>
            ) : (
              <button
                onClick={contactEnterprise}
                className="w-full border border-slate-600 hover:border-slate-400 text-slate-200 hover:text-white font-semibold py-2.5 rounded-xl text-sm transition-colors mb-5"
              >
                Contact sales
              </button>
            )}

            <ul className="space-y-2.5">
              {[
                'Everything in Pro',
                'Unlimited locations',
                'Unlimited seats',
                'Multi-site fleet overview',
                'Custom CMMS integrations',
                'Dedicated onboarding',
                'SLA + priority support',
                'Custom contract & invoicing',
              ].map(f => (
                <li key={f} className="flex items-start gap-2 text-xs text-slate-300">
                  <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Promo code */}
        <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="w-4 h-4 text-indigo-400" />
            <p className="text-sm font-semibold text-white">Have a promo code?</p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={promoCode}
              onChange={e => setPromoCode(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && applyPromo()}
              placeholder="ENTER CODE"
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500 uppercase"
            />
            <button
              onClick={applyPromo}
              disabled={promoLoading || !promoCode.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {promoLoading ? 'Applying…' : 'Apply'}
            </button>
          </div>
          {promoResult && (
            <p className={`mt-2 text-xs font-medium ${promoResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
              {promoResult.message}
            </p>
          )}
        </div>

        {/* Fine print */}
        <p className="text-xs text-slate-600 text-center mt-6">
          Questions? <a href="mailto:support@truesignalapp.com" className="text-indigo-400 hover:text-indigo-300">Contact support</a>
        </p>

      </div>
    </div>
  );
}
