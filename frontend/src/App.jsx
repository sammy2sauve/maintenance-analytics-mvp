import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Nav from './components/Nav';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Overview from './pages/Overview';
import AssetHealth from './pages/AssetHealth';
import PMPlanner from './pages/PMPlanner';
import Help from './pages/Help';
import Settings from './pages/Settings';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import SupportChat from './components/SupportChat';
import OnboardingBanner from './components/OnboardingBanner';
import TrialBanner from './components/TrialBanner';
import Pricing from './pages/Pricing';
import Upgrade from './pages/Upgrade';
import './App.css';

// Pages where the date slicer doesn't apply
const REALTIME_PATHS = ['/dashboard/assets', '/dashboard/pm-planner', '/dashboard/settings', '/dashboard/help'];

function TrueSignalLogo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="44" height="28" viewBox="0 0 44 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="sigGrad" x1="0" y1="0" x2="44" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
          <filter id="sigGlow" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <polyline
          points="0,14 8,14 11,14 14,3 17,25 20,14 22,14 44,14"
          stroke="url(#sigGrad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          fill="none" filter="url(#sigGlow)"
        />
        <circle cx="14" cy="3" r="2.5" fill="#34d399" opacity="0.9" filter="url(#sigGlow)" />
      </svg>
      <div>
        <div className="flex items-baseline gap-1 leading-none">
          <span className="text-lg font-bold text-white tracking-tight">True</span>
          <span className="text-lg font-bold tracking-tight" style={{ color: '#34d399' }}>Signal</span>
        </div>
        <p className="text-[10px] text-indigo-300/70 font-medium tracking-widest uppercase leading-none mt-0.5">
          Maintenance Intelligence
        </p>
      </div>
    </div>
  );
}

function Header({ dateRange, setDateRange }) {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const isRealtime = REALTIME_PATHS.includes(pathname);

  return (
    <header className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border-b border-indigo-800/30 shadow-2xl sticky top-0 z-20">
      <div className="w-full px-6 py-3 flex items-center justify-between">
        <TrueSignalLogo />
        <div className="flex items-center gap-2">
          {isRealtime ? (
            <span className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full">
              Current fleet state — no time filter
            </span>
          ) : (
            <>
              <span className="text-xs text-slate-400">Time Range:</span>
              {[7, 30, 90].map(days => (
                <button
                  key={days}
                  onClick={() => setDateRange(days)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    dateRange === days
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  Last {days}d
                </button>
              ))}
              <button
                onClick={() => setDateRange(null)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  dateRange === null
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                All
              </button>
            </>
          )}
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse ml-3" />
          <span className="text-xs text-emerald-300 font-medium">Live</span>
          {user && (
            <>
              <span className="text-slate-600 ml-2">|</span>
              <span className="text-xs text-slate-400 ml-1">{user.name}</span>
              <button onClick={logout}
                className="text-xs text-slate-500 hover:text-slate-300 ml-1 transition-colors">
                Sign out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

// Redirects to /login if not authenticated
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-400 animate-pulse">Loading…</div>
    </div>
  );
  return user ? children : <Navigate to="/login" replace />;
}

// Redirects viewers (and unauthenticated users) away from settings
function OwnerAdminRoute({ children }) {
  const { user, loading, isOwnerOrAdmin } = useAuth();
  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-400 animate-pulse">Loading…</div>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  if (!isOwnerOrAdmin) return <Navigate to="/dashboard/" replace />;
  return children;
}

function Dashboard() {
  const [dateRange, setDateRange] = useState(30);
  return (
    <div className="h-screen flex flex-col bg-slate-950 overflow-hidden">
      <Header dateRange={dateRange} setDateRange={setDateRange} />
      <Nav basePath="/dashboard" />
      <OnboardingBanner />
      <TrialBanner />
      <div className="flex-1 overflow-hidden relative">
        <div className="pointer-events-none absolute top-0 left-0 right-0 h-10 z-10 bg-gradient-to-b from-slate-950 to-transparent" />
        <Routes>
          <Route path="/"            element={<Overview dateRange={dateRange} />} />
          <Route path="/assets"      element={<AssetHealth />} />
          <Route path="/pm-planner"  element={<PMPlanner />} />
          <Route path="/help"        element={<Help />} />
          <Route path="/upgrade"     element={<Upgrade />} />
          <Route path="/settings"    element={<OwnerAdminRoute><Settings /></OwnerAdminRoute>} />
          <Route path="*"            element={<Navigate to="/dashboard/" replace />} />
        </Routes>
      </div>
      <SupportChat />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/"        element={<Landing />} />
          <Route path="/login"        element={<Login />} />
          <Route path="/signup"       element={<Signup />} />
          <Route path="/verify-email"    element={<VerifyEmail />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password"  element={<ResetPassword />} />
          <Route path="/pricing"      element={<Pricing />} />
          <Route path="/dashboard/*" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
