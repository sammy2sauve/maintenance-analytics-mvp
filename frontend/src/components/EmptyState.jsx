import { Link } from 'react-router-dom';

export default function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-md px-6">
        {/* Plug / connection icon */}
        <svg
          className="mx-auto mb-6"
          width="72" height="72" viewBox="0 0 72 72"
          fill="none" xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="36" cy="36" r="35" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
          {/* Plug prongs */}
          <rect x="24" y="18" width="4" height="14" rx="2" fill="#6366f1" opacity="0.8" />
          <rect x="44" y="18" width="4" height="14" rx="2" fill="#6366f1" opacity="0.8" />
          {/* Plug body */}
          <rect x="20" y="30" width="32" height="10" rx="3" fill="#6366f1" opacity="0.6" />
          {/* Cable */}
          <path d="M36 40 L36 54" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeDasharray="4 3" />
        </svg>

        <h2 className="text-xl font-semibold text-white mb-2">
          No CMMS connected
        </h2>
        <p className="text-sm text-slate-400 mb-6">
          Connect your MaintainX account in Settings to start syncing assets and work orders.
        </p>
        <Link
          to="/dashboard/settings"
          className="inline-block bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          Go to Settings &rarr;
        </Link>
      </div>
    </div>
  );
}
