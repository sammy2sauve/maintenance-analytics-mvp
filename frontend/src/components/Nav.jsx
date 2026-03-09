import { NavLink } from 'react-router-dom';

export default function Nav({ basePath = '' }) {
  const linkClass = ({ isActive }) =>
    `px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
      isActive
        ? 'border-indigo-500 text-white'
        : 'border-transparent text-slate-400 hover:text-slate-200'
    }`;

  return (
    <nav className="bg-slate-900/90 border-b border-slate-700/50 sticky top-[52px] z-10">
      <div className="px-6 flex">
        <NavLink to={`${basePath}/`} end className={linkClass}>Overview</NavLink>
        <NavLink to={`${basePath}/assets`} className={linkClass}>Asset Health</NavLink>
        <NavLink to={`${basePath}/savings`} className={linkClass}>Cost Savings</NavLink>
        <NavLink to={`${basePath}/settings`} className={linkClass}>Settings</NavLink>
      </div>
    </nav>
  );
}
