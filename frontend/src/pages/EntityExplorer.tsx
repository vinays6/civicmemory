import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { politicians } from '../data/mockData';
import { PARTY_COLORS } from '../types';

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

type SortKey = 'name' | 'yearsInOffice' | 'ideology';

function ideologyScore(p: typeof politicians[0]) {
  const vals = Object.values(p.stances);
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
}

function ideologyLabel(score: number) {
  if (score < 30) return { label: `${score} L`, cls: 'prog' };
  if (score > 65) return { label: `${score} R`, cls: 'cons' };
  return { label: `${score} C`, cls: 'swing' };
}

export default function EntityExplorer() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<'all' | 'organizations' | 'individuals'>('all');
  const [sortKey, setSortKey] = useState<SortKey>('ideology');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);

  const results = useMemo(() => {
    let list = [...politicians];
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(p =>
        p.name.toLowerCase().includes(q) ||
        p.state.toLowerCase().includes(q) ||
        p.role.toLowerCase().includes(q) ||
        p.party.toLowerCase().includes(q)
      );
    }
    if (sortKey === 'name') list.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortKey === 'yearsInOffice') list.sort((a, b) => b.yearsInOffice - a.yearsInOffice);
    else list.sort((a, b) => ideologyScore(b) - ideologyScore(a));
    return list;
  }, [query, sortKey]);

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const totalEntities = politicians.length;
  const progressive = politicians.filter(p => ideologyScore(p) < 40).length;
  const conservative = politicians.filter(p => ideologyScore(p) > 60).length;
  const swing = totalEntities - progressive - conservative;
  const pctProg = Math.round((progressive / totalEntities) * 100);
  const pctCons = Math.round((conservative / totalEntities) * 100);
  const pctSwing = 100 - pctProg - pctCons;

  return (
    <div className="h-full overflow-y-auto px-12 pb-16 pt-2">
      {/* Page header */}
      <div className="flex items-end justify-between mb-10 mt-2">
        <div className="max-w-xl">
          <h1 className="text-[3rem] leading-[1.08] font-black tracking-[-0.02em] text-on-surface mb-3">
            Political Entity<br />Database
          </h1>
          <p className="text-base text-on-surface-variant leading-relaxed">
            Analyze and compare individual actors, organizations, and ideological networks.
          </p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-on-surface transition-colors hover:bg-surface-bright"
            style={{ background: '#2a2a2a', border: '1px solid rgba(66,71,84,0.2)' }}>
            <span className="material-symbols-outlined text-[18px]">filter_list</span>
            Filters
          </button>
          <button onClick={() => setCompareOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-primary transition-colors hover:bg-primary/15"
            style={{ background: 'rgba(173,198,255,0.08)', border: '1px solid rgba(173,198,255,0.2)' }}>
            <span className="material-symbols-outlined text-[18px]">compare_arrows</span>
            Compare Entities
            <span className="ml-1 bg-primary text-on-primary text-[10px] font-bold px-1.5 py-0.5 rounded">
              {selected.size}
            </span>
          </button>
        </div>
      </div>

      {/* Bento stats */}
      <div className="grid grid-cols-4 gap-5 mb-10">
        {/* Total */}
        <div className="rounded-xl p-6 relative overflow-hidden"
          style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.15)' }}>
          <span className="material-symbols-outlined absolute -right-3 -bottom-3 text-on-surface-variant opacity-10"
            style={{ fontSize: 100 }}>groups</span>
          <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2">Total Entities</p>
          <p className="text-4xl font-black text-on-surface tracking-tight">{totalEntities}</p>
          <p className="text-xs text-primary mt-2 flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
            +2 this week
          </p>
        </div>

        {/* Active hotspots */}
        <div className="rounded-xl p-6 relative overflow-hidden"
          style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.15)' }}>
          <span className="material-symbols-outlined absolute -right-3 -bottom-3 text-secondary opacity-10"
            style={{ fontSize: 100 }}>flag</span>
          <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2">Active Hotspots</p>
          <p className="text-4xl font-black text-on-surface tracking-tight">5</p>
          <p className="text-xs text-secondary mt-2 flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">trending_up</span>
            High volatility detected
          </p>
        </div>

        {/* Distribution */}
        <div className="col-span-2 rounded-xl p-6 flex items-center justify-between"
          style={{ background: 'linear-gradient(to right, #1c1b1b, #2a2a2a)', border: '1px solid rgba(66,71,84,0.15)' }}>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-4">
              Ideological Distribution
            </p>
            <div className="flex items-end gap-6">
              <div>
                <p className="text-xl font-bold text-blue-400">{pctProg}%</p>
                <p className="text-[10px] uppercase text-on-surface-variant mt-1">Progressive</p>
              </div>
              <div>
                <p className="text-xl font-bold text-red-400">{pctCons}%</p>
                <p className="text-[10px] uppercase text-on-surface-variant mt-1">Conservative</p>
              </div>
              <div>
                <p className="text-xl font-bold text-yellow-400">{pctSwing}%</p>
                <p className="text-[10px] uppercase text-on-surface-variant mt-1">Swing/Neutral</p>
              </div>
            </div>
          </div>
          <div className="w-40 h-2.5 rounded-full overflow-hidden flex">
            <div className="bg-blue-500 h-full opacity-80" style={{ width: `${pctProg}%` }} />
            <div className="bg-yellow-500 h-full opacity-80" style={{ width: `${pctSwing}%` }} />
            <div className="bg-red-500 h-full opacity-80" style={{ width: `${pctCons}%` }} />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.15)' }}>
        {/* Table header actions */}
        <div className="px-6 py-4 flex justify-between items-center"
          style={{ background: 'rgba(14,14,14,0.5)', borderBottom: '1px solid rgba(66,71,84,0.1)' }}>
          <div className="flex gap-5">
            {(['all', 'organizations', 'individuals'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`text-sm pb-1 capitalize transition-colors ${tab === t ? 'text-primary font-semibold border-b-2 border-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>
                {t === 'all' ? 'All Entities' : t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px]">search</span>
              <input type="text" placeholder="Search..." value={query} onChange={e => setQuery(e.target.value)}
                className="bg-surface-container-lowest pl-9 pr-4 py-1.5 rounded-lg text-xs text-on-surface placeholder-on-surface-variant/50 focus:outline-none w-48 transition-all"
                style={{ border: '1px solid rgba(66,71,84,0.2)' }} />
            </div>
            <span className="text-xs text-on-surface-variant">Sort by:</span>
            <select value={sortKey} onChange={e => setSortKey(e.target.value as SortKey)}
              className="bg-surface-container-lowest text-xs text-on-surface rounded px-2 py-1.5 focus:outline-none focus:ring-0"
              style={{ border: '1px solid rgba(66,71,84,0.2)', colorScheme: 'dark' }}>
              <option value="ideology">Ideological Score</option>
              <option value="yearsInOffice">Experience</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr style={{ background: 'rgba(14,14,14,0.3)' }}>
                {['', 'Name', 'Role', 'Locality', 'Ideological Score', 'Major Allies', ''].map((h, i) => (
                  <th key={i} className="py-4 px-6 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                    {i === 0 ? (
                      <input type="checkbox" className="w-4 h-4 rounded accent-primary bg-surface-container-highest" />
                    ) : h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-sm divide-y" style={{ borderColor: 'rgba(66,71,84,0.08)' }}>
              {results.map(p => {
                const score = ideologyScore(p);
                const { label: scoreLbl, cls } = ideologyLabel(score);
                const allies = p.allies.slice(0, 3).map(id => politicians.find(x => x.id === id)).filter(Boolean);
                return (
                  <tr key={p.id} className="group transition-colors hover:bg-surface-bright/20">
                    <td className="py-4 px-6">
                      <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleSelect(p.id)}
                        className="w-4 h-4 rounded accent-primary bg-surface-container-highest" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0"
                          style={{ background: PARTY_COLORS[p.party] }}>
                          {getInitials(p.name)}
                        </div>
                        <div>
                          <p className="font-semibold text-on-surface">{p.name}</p>
                          <p className="text-[11px] text-on-surface-variant">{p.party}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-on-surface-variant text-xs">{p.role}</td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-1.5 text-on-surface-variant text-xs">
                        <span className="material-symbols-outlined text-[13px]">location_on</span>
                        {p.state}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          cls === 'prog' ? 'text-blue-300 bg-blue-500/10' :
                          cls === 'cons' ? 'text-red-300 bg-red-500/10' :
                          'text-yellow-300 bg-yellow-500/10'
                        }`}>
                          {scoreLbl}
                        </span>
                        <div className="w-20 h-1.5 rounded-full overflow-hidden" style={{ background: '#2a2a2a' }}>
                          <div className="h-full rounded-full"
                            style={{
                              width: `${score}%`,
                              background: score < 40 ? '#3B82F6' : score > 65 ? '#EF4444' : '#EAB308',
                            }} />
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex -space-x-1.5">
                        {allies.map(a => a && (
                          <div key={a.id} title={a.name}
                            className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white border"
                            style={{ background: PARTY_COLORS[a.party], borderColor: '#1c1b1b' }}>
                            {getInitials(a.name)}
                          </div>
                        ))}
                        {p.allies.length > 3 && (
                          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] text-on-surface-variant border"
                            style={{ background: '#2a2a2a', borderColor: '#1c1b1b' }}>
                            +{p.allies.length - 3}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button onClick={() => navigate(`/politician/${p.id}`)}
                        className="text-on-surface-variant hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
                        <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 flex items-center justify-between"
          style={{ borderTop: '1px solid rgba(66,71,84,0.08)', background: 'rgba(14,14,14,0.3)' }}>
          <p className="text-xs text-on-surface-variant">
            Showing {results.length} of {politicians.length} entities
          </p>
          <div className="flex gap-1">
            {['chevron_left', '1', 'chevron_right'].map((v, i) => (
              <button key={i}
                className={`w-8 h-8 rounded flex items-center justify-center text-xs transition-colors ${
                  v === '1' ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-bright'
                }`}
                style={{ background: v === '1' ? 'rgba(173,198,255,0.12)' : '#2a2a2a', border: v === '1' ? '1px solid rgba(173,198,255,0.25)' : '1px solid rgba(66,71,84,0.2)' }}>
                {v.startsWith('chevron') ? <span className="material-symbols-outlined text-[18px]">{v}</span> : v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Compare modal */}
      {compareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: 'rgba(19,19,19,0.85)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-xl rounded-xl overflow-hidden shadow-2xl"
            style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.3)' }}>
            <div className="px-6 py-4 flex items-center justify-between"
              style={{ borderBottom: '1px solid rgba(66,71,84,0.1)' }}>
              <h3 className="font-bold text-on-surface">Compare Entities</h3>
              <button onClick={() => setCompareOpen(false)} className="text-on-surface-variant hover:text-on-surface transition-colors">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div className="p-6">
              {selected.size < 2 ? (
                <div className="text-center py-12 rounded-lg text-on-surface-variant"
                  style={{ border: '2px dashed rgba(66,71,84,0.3)' }}>
                  <span className="material-symbols-outlined mb-3 opacity-40" style={{ fontSize: 36 }}>compare</span>
                  <p className="text-sm">Select at least two entities from the database to run a comparative analysis.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {[...selected].slice(0, 2).map(id => {
                    const p = politicians.find(x => x.id === id);
                    if (!p) return null;
                    const score = ideologyScore(p);
                    return (
                      <div key={id} className="p-4 rounded-lg" style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.15)' }}>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-8 h-8 rounded flex items-center justify-center text-xs font-bold text-white"
                            style={{ background: PARTY_COLORS[p.party] }}>
                            {getInitials(p.name)}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-on-surface">{p.name}</p>
                            <p className="text-xs text-on-surface-variant">{p.party}</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          {Object.entries(p.stances).map(([k, v]) => (
                            <div key={k} className="flex items-center gap-2">
                              <span className="text-[10px] text-on-surface-variant capitalize w-20">{k}</span>
                              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: '#2a2a2a' }}>
                                <div className="h-full rounded-full"
                                  style={{ width: `${v}%`, background: v < 50 ? '#3B82F6' : '#EF4444' }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="px-6 py-4 flex justify-end gap-3"
              style={{ background: 'rgba(14,14,14,0.5)', borderTop: '1px solid rgba(66,71,84,0.1)' }}>
              <button onClick={() => setCompareOpen(false)}
                className="px-4 py-2 text-sm text-on-surface-variant hover:text-on-surface transition-colors">
                Cancel
              </button>
              <button disabled={selected.size < 2}
                className="px-4 py-2 text-sm rounded-lg font-medium text-on-primary transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: selected.size >= 2 ? '#adc6ff' : '#353534' }}>
                Run Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
