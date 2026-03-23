import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function TrueSignalMark() {
  return (
    <div className="flex items-center gap-2 justify-center mb-8">
      <svg width="36" height="22" viewBox="0 0 44 28" fill="none">
        <defs>
          <linearGradient id="lg-signup" x1="0" y1="0" x2="44" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
        <polyline points="0,14 8,14 11,14 14,3 17,25 20,14 22,14 44,14"
          stroke="url(#lg-signup)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="14" cy="3" r="2.5" fill="#34d399" />
      </svg>
      <span className="text-xl font-bold text-white tracking-tight">
        True<span style={{ color: '#34d399' }}>Signal</span>
      </span>
    </div>
  );
}

export default function Signup() {
  const { signup } = useAuth();
  const navigate   = useNavigate();

  const [mode, setMode]               = useState('create'); // 'create' | 'join'
  const [name, setName]               = useState('');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [orgName, setOrgName]         = useState('');
  const [inviteCode, setInviteCode]   = useState('');
  const [codePreview, setCodePreview] = useState(null); // null | {org_name, role} | 'error'
  const [codeChecking, setCodeChecking] = useState(false);
  const [error, setError]             = useState('');
  const [loading, setLoading]         = useState(false);

  const checkInviteCode = async (code) => {
    if (!code.trim()) { setCodePreview(null); return; }
    setCodeChecking(true);
    try {
      const res = await api.get(`/invites/validate/${code.trim()}`);
      setCodePreview(res.data);
    } catch {
      setCodePreview('error');
    } finally {
      setCodeChecking(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    if (mode === 'join' && (!inviteCode.trim() || codePreview === 'error' || !codePreview)) {
      setError('Please enter a valid invite code');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'create') {
        await signup(name, email, password, { orgName: orgName.trim() || undefined });
      } else {
        await signup(name, email, password, { inviteCode: inviteCode.trim() });
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Sign up failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <TrueSignalMark />

        <div className="bg-slate-900 border border-slate-700/50 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-lg font-semibold text-white mb-5 text-center">Get started with TrueSignal</h2>

          {/* Mode toggle */}
          <div className="flex rounded-lg bg-slate-800 p-1 mb-6">
            <button
              type="button"
              onClick={() => { setMode('create'); setError(''); }}
              className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-colors ${
                mode === 'create' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create organization
            </button>
            <button
              type="button"
              onClick={() => { setMode('join'); setError(''); }}
              className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-colors ${
                mode === 'join' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Join with invite code
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Full Name</label>
              <input
                type="text" required autoFocus
                value={name} onChange={e => setName(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="Jane Smith"
              />
            </div>

            {mode === 'create' && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Organization Name</label>
                <input
                  type="text"
                  value={orgName} onChange={e => setOrgName(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  placeholder="Acme Facilities"
                />
              </div>
            )}

            {mode === 'join' && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Invite Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={e => { setInviteCode(e.target.value); setCodePreview(null); }}
                  onBlur={e => checkInviteCode(e.target.value)}
                  className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none transition-colors ${
                    codePreview === 'error'
                      ? 'border-red-500 focus:border-red-500'
                      : codePreview
                      ? 'border-emerald-500 focus:border-emerald-500'
                      : 'border-slate-700 focus:border-indigo-500'
                  }`}
                  placeholder="Paste your invite code"
                />
                {codeChecking && (
                  <p className="text-xs text-slate-400 mt-1">Checking code…</p>
                )}
                {codePreview && codePreview !== 'error' && (
                  <p className="text-xs text-emerald-400 mt-1">
                    Joining <span className="font-semibold">{codePreview.org_name}</span> as{' '}
                    <span className="capitalize">{codePreview.role}</span>
                  </p>
                )}
                {codePreview === 'error' && (
                  <p className="text-xs text-red-400 mt-1">Invalid, expired, or already used code</p>
                )}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Work Email</label>
              <input
                type="email" required
                value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
              <input
                type="password" required
                value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="Min. 8 characters"
              />
            </div>

            {error && (
              <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">{error}</p>
            )}

            <button
              type="submit" disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
            >
              {loading
                ? (mode === 'create' ? 'Creating account…' : 'Joining…')
                : (mode === 'create' ? 'Create Account' : 'Join Organization')
              }
            </button>
          </form>

          <p className="text-xs text-slate-500 text-center mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">Sign in</Link>
          </p>
        </div>

        <p className="text-center text-xs text-slate-600 mt-4">
          By signing up you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
