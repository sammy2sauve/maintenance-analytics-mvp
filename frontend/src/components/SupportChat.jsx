import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Maximize2, Minimize2, X, Send, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// Call this from anywhere to pop the widget open
export function openSupportChat(prefill = '') {
  window.dispatchEvent(new CustomEvent('open-support-chat', { detail: { prefill } }));
}

const GREETING = {
  role: 'support',
  text: "Hi! I'm the TrueSignal support team. Send us a message and we'll get back to you within one business day.",
};

export default function SupportChat() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  // Listen for the global open event (triggered by Help page buttons)
  useEffect(() => {
    const handler = (e) => {
      setOpen(true);
      setSent(false);
      setError(null);
      if (e.detail?.prefill) setSubject(e.detail.prefill);
    };
    window.addEventListener('open-support-chat', handler);
    return () => window.removeEventListener('open-support-chat', handler);
  }, []);

  // Pre-fill name/email from logged-in user
  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setEmail(user.email || '');
    }
  }, [user]);

  // Focus textarea when opening
  useEffect(() => {
    if (open) setTimeout(() => textareaRef.current?.focus(), 80);
  }, [open]);

  const handleSend = async () => {
    if (!message.trim()) return;
    setSending(true);
    setError(null);
    try {
      await api.post('/support/message', {
        name: name.trim(),
        email: email.trim(),
        subject: subject.trim() || 'Support request',
        message: message.trim(),
      });
      setSent(true);
      setMessage('');
      setSubject('');
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Could not send message. Email us at support@truesignalapp.com'
      );
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSend();
  };

  const close = () => { setOpen(false); setFullscreen(false); };

  // ── Minimized pill ─────────────────────────────────────────────────────────
  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); setSent(false); setError(null); }}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-full shadow-xl shadow-indigo-900/50 transition-all hover:scale-105 active:scale-95"
      >
        <MessageSquare className="w-4 h-4" />
        Support
      </button>
    );
  }

  // ── Open panel ─────────────────────────────────────────────────────────────
  return (
    <div
      className={`fixed z-50 flex flex-col bg-slate-900 border border-slate-700/60 shadow-2xl shadow-black/60 transition-all duration-200 ${
        fullscreen
          ? 'inset-0 rounded-none'
          : 'bottom-6 right-6 w-[400px] rounded-2xl'
      }`}
      style={fullscreen ? {} : { height: 520 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-indigo-950/80 to-slate-900 border-b border-slate-700/50 flex-shrink-0 rounded-t-2xl">
        <div className="p-1.5 bg-indigo-600/20 rounded-lg border border-indigo-500/20">
          <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white leading-none">TrueSignal Support</p>
          <p className="text-[10px] text-emerald-400 mt-0.5 leading-none">Usually replies within 1 business day</p>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setFullscreen(f => !f)}
            className="p-1.5 rounded-lg hover:bg-slate-700/60 text-slate-500 hover:text-slate-300 transition-colors"
            title={fullscreen ? 'Minimize' : 'Fullscreen'}
          >
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={close}
            className="p-1.5 rounded-lg hover:bg-slate-700/60 text-slate-500 hover:text-slate-300 transition-colors"
            title="Minimize to button"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={close}
            className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-colors"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

        {/* Greeting bubble */}
        <div className="flex gap-2.5">
          <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
            <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="bg-slate-800/80 border border-slate-700/40 rounded-xl rounded-tl-sm px-3.5 py-2.5 max-w-[85%]">
            <p className="text-xs text-slate-300 leading-relaxed">{GREETING.text}</p>
          </div>
        </div>

        {sent && (
          <div className="flex gap-2.5">
            <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl rounded-tl-sm px-3.5 py-2.5 max-w-[85%]">
              <p className="text-xs text-emerald-400 font-medium">Message received!</p>
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                We'll get back to you at {email || 'your email'} within one business day.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Form */}
      {!sent && (
        <div className="flex-shrink-0 border-t border-slate-700/50 px-4 py-3 space-y-2.5">
          {/* Name + email row (hidden if pre-filled) */}
          {!user && (
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Your name"
                value={name}
                onChange={e => setName(e.target.value)}
                className="bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
              />
              <input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
              />
            </div>
          )}

          {/* Subject */}
          <input
            type="text"
            placeholder="Subject (optional)"
            value={subject}
            onChange={e => setSubject(e.target.value)}
            className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />

          {/* Message */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              placeholder="Describe your issue or question…"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={fullscreen ? 6 : 3}
              className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors resize-none"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-600">⌘ Enter to send</span>
            <button
              onClick={handleSend}
              disabled={sending || !message.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="w-3 h-3" />
              {sending ? 'Sending…' : 'Send message'}
            </button>
          </div>
        </div>
      )}

      {sent && (
        <div className="flex-shrink-0 border-t border-slate-700/50 px-4 py-3">
          <button
            onClick={() => { setSent(false); setMessage(''); }}
            className="w-full py-2 text-xs text-slate-400 hover:text-white transition-colors"
          >
            Send another message
          </button>
        </div>
      )}
    </div>
  );
}
