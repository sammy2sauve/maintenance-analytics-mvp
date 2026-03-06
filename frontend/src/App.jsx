import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Nav from './components/Nav';
import Overview from './pages/Overview';
import AssetHealth from './pages/AssetHealth';
import CostSavings from './pages/CostSavings';
import './App.css';

function Header({ dateRange, setDateRange }) {
  return (
    <header className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border-b border-indigo-800/30 shadow-2xl sticky top-0 z-20">
      <div className="w-full px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Maintenance Analytics</h1>
          <p className="text-xs text-indigo-300 font-medium">TrueSignal Intelligence Platform</p>
        </div>
        <div className="flex items-center gap-2">
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
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse ml-3"></div>
          <span className="text-xs text-emerald-300 font-medium">Live</span>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const [dateRange, setDateRange] = useState(30);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <Header dateRange={dateRange} setDateRange={setDateRange} />
        <Nav />
        <Routes>
          <Route path="/" element={<Overview dateRange={dateRange} />} />
          <Route path="/assets" element={<AssetHealth dateRange={dateRange} />} />
          <Route path="/savings" element={<CostSavings dateRange={dateRange} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
