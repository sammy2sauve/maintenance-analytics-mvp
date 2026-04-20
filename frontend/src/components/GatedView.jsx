import { useNavigate } from 'react-router-dom';
import { Link2, ArrowRight } from 'lucide-react';

/**
 * GatedView — wraps a page skeleton in blur + overlay when user has no CMMS connected.
 *
 * Props:
 *   title       — overlay card headline e.g. "Fleet overview"
 *   description — one-liner explaining what they'll see
 *   skeleton    — JSX of the blurred ghost layout
 */
export default function GatedView({ title, description, skeleton }) {
  const navigate = useNavigate();

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Blurred skeleton behind */}
      <div className="absolute inset-0 blur-sm opacity-25 pointer-events-none select-none" aria-hidden>
        {skeleton}
      </div>

      {/* Dark overlay gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/60 via-slate-950/40 to-slate-950/80 pointer-events-none" />

      {/* Centered unlock card */}
      <div className="absolute inset-0 flex items-center justify-center p-6">
        <div className="relative max-w-sm w-full bg-slate-900/90 border border-indigo-500/30 rounded-2xl p-8 text-center shadow-2xl shadow-black/50"
          style={{ backdropFilter: 'blur(12px)' }}
        >
          {/* Glow ring */}
          <div className="absolute inset-0 rounded-2xl bg-indigo-500/5 pointer-events-none" />

          {/* Icon */}
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 mb-5 mx-auto">
            <Link2 className="w-5 h-5 text-indigo-400" />
          </div>

          {/* Text */}
          <h2 className="text-base font-semibold text-white mb-2">{title}</h2>
          <p className="text-sm text-slate-400 leading-relaxed mb-6">{description}</p>

          {/* CTA */}
          <button
            onClick={() => navigate('/dashboard/settings')}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-900/40"
          >
            Connect FaciliWorks
            <ArrowRight className="w-4 h-4" />
          </button>

          <p className="text-[11px] text-slate-600 mt-4">
            Your CMMS data stays private and encrypted
          </p>
        </div>
      </div>
    </div>
  );
}
