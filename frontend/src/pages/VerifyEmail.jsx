import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading | success | error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      setStatus('error');
      setMessage('No verification token found in the link.');
      return;
    }

    fetch(`${API_BASE}/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(async res => {
        const data = await res.json();
        if (res.ok) {
          setStatus('success');
        } else {
          setStatus('error');
          setMessage(data.detail || 'Verification failed.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Could not reach the server. Please try again.');
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="bg-slate-900 border border-slate-700/50 rounded-2xl p-10 max-w-sm w-full text-center shadow-2xl">

        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold text-white">True</span>
            <span className="text-xl font-bold" style={{ color: '#34d399' }}>Signal</span>
          </div>
        </div>

        {status === 'loading' && (
          <>
            <Loader className="w-12 h-12 text-indigo-400 mx-auto mb-4 animate-spin" />
            <p className="text-slate-300 text-sm">Verifying your email…</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
            <h1 className="text-white text-xl font-bold mb-2">Email verified</h1>
            <p className="text-slate-400 text-sm mb-6">
              Your account is now active. You can sign in and start using TrueSignal.
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Sign In
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h1 className="text-white text-xl font-bold mb-2">Verification failed</h1>
            <p className="text-slate-400 text-sm mb-6">
              {message || 'This link is invalid or has already been used.'}
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Back to Sign In
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
