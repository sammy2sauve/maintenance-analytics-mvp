import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RefreshCw } from 'lucide-react';

function formatLastSynced(date) {
  if (!date) return null;
  const secs = Math.floor((Date.now() - date.getTime()) / 1000);
  if (secs < 60) return 'just now';
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

export default function Nav({ basePath = '' }) {
  const { hasApiKey, syncing, lastSynced, triggerSync } = useAuth();

  const linkClass = ({ isActive }) =>
    `px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
      isActive
        ? 'border-indigo-500 text-white'
        : 'border-transparent text-slate-400 hover:text-slate-200'
    }`;

  return (
    <nav className="bg-slate-900/90 border-b border-slate-700/50 sticky top-[52px] z-10">
      <div className="px-6 flex items-center justify-between">
        <div className="flex">
          <NavLink to={`${basePath}/`} end className={linkClass}>Overview</NavLink>
          <NavLink to={`${basePath}/assets`} className={linkClass}>Asset Health</NavLink>
          <NavLink to={`${basePath}/reports`} className={linkClass}>Reports &amp; Alerts</NavLink>
          <NavLink to={`${basePath}/settings`} className={linkClass}>Settings</NavLink>
          <NavLink to={`${basePath}/help`} className={linkClass}>Help</NavLink>
        </div>

        {hasApiKey && (
          <div className="flex items-center gap-2">
            {lastSynced && (
              <span className="text-[11px] text-slate-500">
                Synced {formatLastSynced(lastSynced)}
              </span>
            )}
            <button
              onClick={() => triggerSync()}
              disabled={syncing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all ${
                syncing
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-slate-800 text-slate-300 hover:bg-indigo-700 hover:text-white'
              }`}
            >
              <RefreshCw className={`w-3 h-3 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing…' : 'Sync'}
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
