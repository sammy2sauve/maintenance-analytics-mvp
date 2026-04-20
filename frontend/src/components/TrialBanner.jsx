import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Zap, AlertTriangle } from 'lucide-react';

export default function TrialBanner() {
  const { trialActive, trialExpired, trialDaysLeft } = useAuth();

  if (!trialActive && !trialExpired) return null;

  const urgent = trialDaysLeft !== null && trialDaysLeft <= 5;

  if (trialExpired) {
    return (
      <div className="flex-shrink-0 bg-red-950/60 border-b border-red-500/30 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
          <p className="text-xs text-red-300 font-medium">
            Your free trial has ended. Upgrade to continue using TrueSignal.
          </p>
        </div>
        <Link
          to="/dashboard/upgrade"
          className="flex-shrink-0 flex items-center gap-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          <Zap className="w-3 h-3" />
          Upgrade now
        </Link>
      </div>
    );
  }

  return (
    <div className={`flex-shrink-0 border-b px-4 py-2 flex items-center justify-between ${
      urgent
        ? 'bg-amber-950/40 border-amber-500/30'
        : 'bg-indigo-950/40 border-indigo-500/20'
    }`}>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${urgent ? 'bg-amber-400 animate-pulse' : 'bg-indigo-400'}`} />
        <p className={`text-xs font-medium ${urgent ? 'text-amber-300' : 'text-indigo-300'}`}>
          {urgent
            ? `${trialDaysLeft} day${trialDaysLeft === 1 ? '' : 's'} left in your trial — upgrade to keep access`
            : `Free trial · ${trialDaysLeft} days remaining`}
        </p>
      </div>
      <Link
        to="/dashboard/upgrade"
        className={`flex-shrink-0 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
          urgent
            ? 'bg-amber-500 hover:bg-amber-400 text-slate-900'
            : 'bg-indigo-600/60 hover:bg-indigo-600 text-white border border-indigo-500/40'
        }`}
      >
        <Zap className="w-3 h-3" />
        Upgrade to Pro
      </Link>
    </div>
  );
}
