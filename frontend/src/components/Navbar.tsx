import { Link, useLocation } from 'react-router-dom';
import { Map, Network, Search, Globe, BarChart2 } from 'lucide-react';

const navLinks = [
  { to: '/map', label: 'Map', icon: Map },
  { to: '/network', label: 'Network', icon: Network },
  { to: '/search', label: 'Search', icon: Search },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Globe size={16} className="text-white" />
            </div>
            <span className="text-white font-bold text-lg tracking-tight">
              un<span className="text-blue-400">bais</span>
            </span>
            <span className="hidden sm:block text-slate-500 text-xs font-normal ml-1 border border-slate-700 rounded px-1.5 py-0.5">
              Political Intelligence
            </span>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {navLinks.map(({ to, label, icon: Icon }) => {
              const active = location.pathname === to || location.pathname.startsWith(to + '/');
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <Icon size={15} />
                  <span className="hidden sm:block">{label}</span>
                </Link>
              );
            })}

            <div className="ml-2 pl-2 border-l border-slate-800 flex items-center gap-1">
              <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
                <BarChart2 size={15} />
                <span className="hidden sm:block">Compare</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
