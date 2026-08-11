import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CheckCircle2, Circle, ArrowRight, X } from 'lucide-react';

const DISMISS_KEY = 'ts_onboarding_dismissed';

export default function OnboardingBanner() {
  const { hasApiKey } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISS_KEY) === '1'
  );
  const [hiding, setHiding] = useState(false);

  // Auto-hide with fade once connected
  useEffect(() => {
    if (hasApiKey && !dismissed) {
      setHiding(true);
      const t = setTimeout(() => setDismissed(true), 800);
      return () => clearTimeout(t);
    }
  }, [hasApiKey]);

  if (dismissed || hasApiKey) return null;

  const dismiss = () => {
    setHiding(true);
    setTimeout(() => {
      localStorage.setItem(DISMISS_KEY, '1');
      setDismissed(true);
    }, 300);
  };

  return (
    <div
      className={`flex-shrink-0 border-b border-indigo-500/20 bg-indigo-950/40 px-6 transition-all duration-300 ${
        hiding ? 'opacity-0 max-h-0 py-0 overflow-hidden' : 'opacity-100 max-h-16 py-2.5'
      }`}
    >
      <div className="flex items-center gap-6">
        {/* Label */}
        <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-widest whitespace-nowrap flex-shrink-0">
          Get started
        </span>

        {/* Steps */}
        <div className="flex items-center gap-2 flex-1">
          {/* Step 1 — done */}
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span className="text-xs text-emerald-400 font-medium whitespace-nowrap">Account created</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />

          {/* Step 2 — pending */}
          <button
            onClick={() => navigate('/dashboard/settings')}
            className="flex items-center gap-1.5 group"
          >
            <Circle className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            <span className="text-xs text-indigo-300 font-medium group-hover:text-white transition-colors whitespace-nowrap">
              Connect FaciliWorks
            </span>
          </button>

          {/* Hint */}
          <span className="text-[11px] text-slate-600 hidden sm:inline">
            — connect your CMMS to unlock predictive insights
          </span>
        </div>

        {/* CTA */}
        <button
          onClick={() => navigate('/dashboard/settings')}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors"
        >
          Go to Settings
          <ArrowRight className="w-3 h-3" />
        </button>

        {/* Dismiss */}
        <button
          onClick={dismiss}
          className="flex-shrink-0 p-1 text-slate-600 hover:text-slate-400 transition-colors"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
