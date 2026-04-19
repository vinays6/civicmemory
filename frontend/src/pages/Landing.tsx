import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Map, Network, ChevronRight, Zap, Globe, BarChart2 } from 'lucide-react';
import { politicians } from '../data/mockData';
import PoliticianCard from '../components/PoliticianCard';
import { PARTY_COLORS } from '../types';

const STATS = [
  { label: 'Politicians Tracked', value: '13' },
  { label: 'Regions Covered', value: '12' },
  { label: 'Issues Analyzed', value: '6' },
  { label: 'Relationships Mapped', value: '23' },
];

const FEATURES = [
  {
    icon: Map,
    title: 'Regional Map',
    desc: 'Explore political figures across the country. Click any marker to see profiles, stances, and connections.',
  },
  {
    icon: Network,
    title: 'Alliance Network',
    desc: 'Visualize political alliances and rivalries as a live force-directed graph. Understand who aligns with whom.',
  },
  {
    icon: BarChart2,
    title: 'Stance Analysis',
    desc: 'See where any politician stands on healthcare, climate, immigration, and more — backed by data.',
  },
];

export default function Landing() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const featured = politicians.slice(0, 6);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  const partyCounts = politicians.reduce<Record<string, number>>((acc, p) => {
    acc[p.party] = (acc[p.party] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Hero */}
      <div className="relative overflow-hidden pt-32 pb-24 px-4">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-600/5 blur-3xl rounded-full" />
          <div className="absolute top-20 left-1/4 w-[300px] h-[300px] bg-blue-500/5 blur-3xl rounded-full" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-600/10 border border-blue-600/20 text-blue-400 text-xs font-medium mb-6">
            <Zap size={12} />
            AI-Powered Political Intelligence
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-white mb-6 leading-tight tracking-tight">
            Understand politics{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-600">
              without the bias
            </span>
          </h1>

          <p className="text-lg text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            unbais uses AI agents to extract and map political information across regions — from
            national figures to local officials — giving you clear, data-driven insights into who
            represents you.
          </p>

          {/* Search bar */}
          <form onSubmit={handleSearch} className="max-w-xl mx-auto mb-6">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search politicians, states, issues..."
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
                />
              </div>
              <button
                type="submit"
                className="px-5 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2"
              >
                Search
                <ChevronRight size={14} />
              </button>
            </div>
          </form>

          {/* Quick links */}
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button
              onClick={() => navigate('/map')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-600 text-slate-400 hover:text-slate-200 text-sm transition-colors"
            >
              <Map size={14} />
              Explore Map
            </button>
            <button
              onClick={() => navigate('/network')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-600 text-slate-400 hover:text-slate-200 text-sm transition-colors"
            >
              <Network size={14} />
              View Network
            </button>
            <button
              onClick={() => navigate('/search')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-600 text-slate-400 hover:text-slate-200 text-sm transition-colors"
            >
              <Globe size={14} />
              Browse All
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="max-w-6xl mx-auto px-4 mb-20">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {STATS.map(s => (
            <div key={s.label} className="p-5 rounded-xl bg-slate-900 border border-slate-800 text-center">
              <div className="text-2xl font-bold text-white mb-1">{s.value}</div>
              <div className="text-xs text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Party breakdown */}
      <div className="max-w-6xl mx-auto px-4 mb-20">
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Party Breakdown</h2>
          <div className="flex items-end gap-3 h-16">
            {Object.entries(partyCounts).map(([party, count]) => {
              const color = PARTY_COLORS[party as keyof typeof PARTY_COLORS];
              const pct = (count / politicians.length) * 100;
              return (
                <div key={party} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs text-slate-400">{count}</span>
                  <div
                    className="w-full rounded-t-sm transition-all"
                    style={{ height: `${pct * 0.8 + 8}px`, backgroundColor: color, opacity: 0.8 }}
                  />
                  <span className="text-xs text-slate-500 truncate w-full text-center">
                    {party}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-4 mb-20">
        <h2 className="text-2xl font-bold text-white mb-2">How it works</h2>
        <p className="text-slate-500 mb-8 text-sm">
          AI agents continuously extract political data so you don't have to.
        </p>
        <div className="grid sm:grid-cols-3 gap-4">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="p-6 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-blue-600/15 border border-blue-600/20 flex items-center justify-center mb-4">
                <Icon size={18} className="text-blue-400" />
              </div>
              <h3 className="font-semibold text-slate-100 mb-2">{title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Featured politicians */}
      <div className="max-w-6xl mx-auto px-4 pb-20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-white">Featured Politicians</h2>
            <p className="text-slate-500 text-sm mt-1">Click any card to see their full profile</p>
          </div>
          <button
            onClick={() => navigate('/search')}
            className="flex items-center gap-1 text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            View all <ChevronRight size={14} />
          </button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {featured.map(p => (
            <PoliticianCard key={p.id} politician={p} />
          ))}
        </div>
      </div>
    </div>
  );
}
