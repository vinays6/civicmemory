import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { politicians, networkEdges } from '../data/mockData';
import { Party, PARTY_COLORS } from '../types';

interface SimNode {
  id: string; name: string; party: Party; role: string;
  x: number; y: number; vx: number; vy: number;
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

function runStep(nodes: SimNode[], edges: typeof networkEdges, w: number, h: number): SimNode[] {
  const cx = w / 2, cy = h / 2;
  const next = nodes.map(n => ({ ...n }));
  for (let i = 0; i < next.length; i++) {
    const n = next[i];
    let fx = 0, fy = 0;
    for (let j = 0; j < next.length; j++) {
      if (i === j) continue;
      const m = next[j];
      const dx = n.x - m.x, dy = n.y - m.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = 4000 / (dist * dist);
      fx += (dx / dist) * force; fy += (dy / dist) * force;
    }
    for (const e of edges) {
      if (e.source !== n.id && e.target !== n.id) continue;
      const otherId = e.source === n.id ? e.target : e.source;
      const other = next.find(m => m.id === otherId);
      if (!other) continue;
      const dx = other.x - n.x, dy = other.y - n.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ideal = e.type === 'ally' ? 110 : 240;
      const force = 0.06 * (dist - ideal) * e.strength;
      fx += (dx / dist) * force; fy += (dy / dist) * force;
    }
    fx += (cx - n.x) * 0.025; fy += (cy - n.y) * 0.025;
    n.vx = (n.vx + fx) * 0.82; n.vy = (n.vy + fy) * 0.82;
    n.x = Math.max(28, Math.min(w - 28, n.x + n.vx));
    n.y = Math.max(28, Math.min(h - 28, n.y + n.vy));
  }
  return next;
}

const IDEOLOGY_FILTERS = [
  { label: 'Red', color: '#EF4444', party: 'Republican' as Party },
  { label: 'Blue', color: '#3B82F6', party: 'Democrat' as Party },
  { label: 'Yellow', color: '#EAB308', party: 'Independent' as Party },
  { label: 'Gray', color: '#6B7280', party: 'Libertarian' as Party },
];

export default function NetworkDashboard() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef(0);
  const stepsRef = useRef(0);
  const [dims, setDims] = useState({ w: 600, h: 500 });
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>('joe-biden');
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<Party[]>([]);
  const [showPoliticians, setShowPoliticians] = useState(true);
  const [showOrgs, setShowOrgs] = useState(true);
  const [minStrength, setMinStrength] = useState(0.5);

  function initNodes(w: number, h: number): SimNode[] {
    return politicians.map((p, i) => {
      const angle = (i / politicians.length) * Math.PI * 2;
      const r = Math.min(w, h) * 0.28;
      return { id: p.id, name: p.name, party: p.party, role: p.role,
        x: w / 2 + Math.cos(angle) * r + (Math.random() - 0.5) * 30,
        y: h / 2 + Math.sin(angle) * r + (Math.random() - 0.5) * 30,
        vx: 0, vy: 0 };
    });
  }

  useEffect(() => {
    function measure() {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDims({ w: width, h: height });
      }
    }
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  useEffect(() => {
    if (dims.w > 0) { setNodes(initNodes(dims.w, dims.h)); stepsRef.current = 0; }
  }, [dims.w, dims.h]);

  useEffect(() => {
    if (!nodes.length) return;
    function tick() {
      if (stepsRef.current < 250) {
        setNodes(prev => runStep(prev, networkEdges, dims.w, dims.h));
        stepsRef.current++;
        animRef.current = requestAnimationFrame(tick);
      }
    }
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes.length, dims.w, dims.h]);

  const visibleIds = new Set(
    nodes
      .filter(n => activeFilters.length === 0 || activeFilters.includes(n.party))
      .map(n => n.id)
  );

  const filteredEdges = networkEdges.filter(e =>
    visibleIds.has(e.source) && visibleIds.has(e.target) && e.strength >= minStrength * 3
  );

  const selectedPolitician = selectedId ? politicians.find(p => p.id === selectedId) : null;
  const selectedNode = selectedId ? nodes.find(n => n.id === selectedId) : null;

  function toggleFilter(party: Party) {
    setActiveFilters(prev => prev.includes(party) ? prev.filter(p => p !== party) : [...prev, party]);
  }

  return (
    <div className="h-full flex overflow-hidden">
      {/* Parameters panel */}
      <aside className="w-56 flex-shrink-0 flex flex-col overflow-y-auto"
        style={{ background: '#0e0e0e' }}>
        <div className="p-5 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(66,71,84,0.1)' }}>
          <h2 className="text-sm font-semibold text-on-surface">Parameters</h2>
          <button className="text-on-surface-variant hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-[18px]">add</span>
          </button>
        </div>
        <div className="p-5 space-y-7 flex-1">
          {/* Entity types */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">
              Entity Types
            </label>
            <div className="space-y-2">
              {[
                { label: 'Politicians', state: showPoliticians, toggle: () => setShowPoliticians(v => !v) },
                { label: 'Organizations', state: showOrgs, toggle: () => setShowOrgs(v => !v) },
              ].map(({ label, state, toggle }) => (
                <label key={label} className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors hover:bg-surface-container-low"
                  style={{ border: '1px solid rgba(66,71,84,0.1)' }}>
                  <input type="checkbox" checked={state} onChange={toggle}
                    className="w-4 h-4 rounded accent-primary bg-surface-container-highest focus:ring-0" />
                  <span className="text-sm font-medium text-on-surface">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Ideology filters */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">
              Ideology Focus
            </label>
            <div className="flex flex-wrap gap-2">
              {IDEOLOGY_FILTERS.map(({ label, color, party }) => {
                const active = activeFilters.includes(party);
                return (
                  <button key={label} onClick={() => toggleFilter(party)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all"
                    style={{
                      background: active ? `${color}18` : '#2a2a2a',
                      border: `1px solid ${active ? `${color}60` : 'rgba(66,71,84,0.2)'}`,
                      color: active ? color : '#c2c6d6',
                    }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Min strength */}
          <div>
            <div className="flex justify-between items-end mb-3">
              <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                Min Strength
              </label>
              <span className="text-xs font-mono text-primary">{minStrength.toFixed(2)}</span>
            </div>
            <input type="range" min={0} max={1} step={0.05} value={minStrength}
              onChange={e => setMinStrength(Number(e.target.value))}
              className="w-full h-1 rounded-lg appearance-none cursor-pointer accent-primary bg-surface-container-highest" />
            <div className="flex justify-between text-[10px] text-on-surface-variant/50 mt-2">
              <span>Loose</span><span>Direct</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Graph canvas */}
      <section ref={containerRef} className="flex-1 relative overflow-hidden"
        style={{ background: '#0e0e0e' }}>
        <div className="absolute inset-0 grid-bg pointer-events-none z-0" />

        {/* Zoom controls */}
        <div className="absolute top-4 right-4 z-20 flex flex-col rounded-lg p-1"
          style={{ background: 'rgba(28,27,27,0.85)', backdropFilter: 'blur(12px)', border: '1px solid rgba(66,71,84,0.15)' }}>
          {['add', 'remove', 'aspect_ratio'].map((icon, i) => (
            <button key={icon} onClick={() => i === 2 && (setNodes(initNodes(dims.w, dims.h)), (stepsRef.current = 0))}
              className="p-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-bright transition-colors">
              <span className="material-symbols-outlined text-[18px]">{icon}</span>
            </button>
          ))}
        </div>

        <svg width={dims.w} height={dims.h} className="absolute inset-0">
          {/* Edges */}
          {filteredEdges.map((edge, i) => {
            const src = nodes.find(n => n.id === edge.source);
            const tgt = nodes.find(n => n.id === edge.target);
            if (!src || !tgt) return null;
            const highlighted = hoveredId === edge.source || hoveredId === edge.target
              || selectedId === edge.source || selectedId === edge.target;
            const dimmed = (hoveredId || selectedId) && !highlighted;
            const color = edge.type === 'ally' ? '#3B82F6' : '#EF4444';
            return (
              <line key={i} x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                stroke={color}
                strokeWidth={edge.strength * 0.8}
                strokeOpacity={dimmed ? 0.03 : highlighted ? 0.7 : 0.2}
                strokeDasharray={edge.type === 'opponent' ? '5 4' : undefined} />
            );
          })}

          {/* Nodes */}
          {nodes.map(node => {
            if (!visibleIds.has(node.id)) return null;
            const color = PARTY_COLORS[node.party];
            const isSelected = node.id === selectedId;
            const isHovered = node.id === hoveredId;
            const connected = filteredEdges.some(e => e.source === node.id || e.target === node.id);
            const isDimmed = (hoveredId || selectedId) && !isSelected && !isHovered && !connected;
            const r = 20;

            return (
              <g key={node.id} transform={`translate(${node.x},${node.y})`} style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => setSelectedId(prev => prev === node.id ? null : node.id)}>
                {isSelected && <circle r={r + 10} fill={color} fillOpacity={0.08} stroke={color} strokeOpacity={0.2} />}
                <circle r={r} fill={color} fillOpacity={isDimmed ? 0.12 : 0.85}
                  stroke={isSelected ? '#ffffff' : color}
                  strokeWidth={isSelected ? 2 : 1}
                  strokeOpacity={isDimmed ? 0.08 : 0.9} />
                <text textAnchor="middle" dominantBaseline="central" fill="#fff"
                  fillOpacity={isDimmed ? 0.15 : 1} fontSize={9} fontWeight={700}>
                  {getInitials(node.name)}
                </text>
                {(isHovered || isSelected) && (
                  <text y={r + 13} textAnchor="middle" fill="#e5e2e1" fontSize={10} fontWeight={600}>
                    {node.name.split(' ').slice(-1)[0]}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 p-3 rounded-lg text-xs space-y-2"
          style={{ background: 'rgba(28,27,27,0.9)', backdropFilter: 'blur(12px)', border: '1px solid rgba(66,71,84,0.15)' }}>
          <p className="text-on-surface-variant font-medium">Connections</p>
          <div className="flex items-center gap-2 text-on-surface-variant">
            <div className="w-6 border-t-2 border-blue-500" /> Ally
          </div>
          <div className="flex items-center gap-2 text-on-surface-variant">
            <div className="w-6 border-t-2 border-red-500 border-dashed" /> Opponent
          </div>
        </div>
      </section>

      {/* Context inspector */}
      {selectedPolitician ? (
        <aside className="w-72 flex-shrink-0 flex flex-col overflow-hidden"
          style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.1)', borderTop: 'none', borderBottom: 'none' }}>
          {/* Header */}
          <div className="p-6 relative"
            style={{ background: 'linear-gradient(to bottom, #2a2a2a, transparent)', borderBottom: '1px solid rgba(66,71,84,0.1)' }}>
            <button onClick={() => setSelectedId(null)}
              className="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface transition-colors">
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
            <div className="flex items-start gap-4 mt-2">
              <div className="w-14 h-14 rounded-lg flex items-center justify-center font-bold text-lg text-white flex-shrink-0"
                style={{ background: `${PARTY_COLORS[selectedPolitician.party]}20`, border: `1px solid ${PARTY_COLORS[selectedPolitician.party]}40` }}>
                {getInitials(selectedPolitician.name)}
                <div className="absolute bottom-0 right-0 w-3 h-3 rounded-tl"
                  style={{ background: PARTY_COLORS[selectedPolitician.party] }} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-on-surface leading-tight tracking-tight">
                  {selectedPolitician.name}
                </h3>
                <p className="text-sm text-on-surface-variant mt-0.5">{selectedPolitician.role}, {selectedPolitician.stateCode}</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-on-surface-variant"
                    style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.2)' }}>
                    {selectedPolitician.party}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-7">
            {/* Key stances */}
            <div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">psychology</span> Key Stances
              </h4>
              <ul className="space-y-3">
                {selectedPolitician.tags.slice(0, 3).map(tag => (
                  <li key={tag} className="flex items-start gap-3">
                    <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                      style={{ background: PARTY_COLORS[selectedPolitician.party] }} />
                    <p className="text-sm text-on-surface capitalize">{tag.replace(/-/g, ' ')}</p>
                  </li>
                ))}
              </ul>
            </div>

            {/* Connection evidence */}
            <div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">link</span> Connections
              </h4>
              <div className="rounded-lg overflow-hidden" style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.1)' }}>
                {networkEdges
                  .filter(e => e.source === selectedId || e.target === selectedId)
                  .slice(0, 5)
                  .map((e, i) => {
                    const otherId = e.source === selectedId ? e.target : e.source;
                    const other = politicians.find(p => p.id === otherId);
                    if (!other) return null;
                    return (
                      <div key={i} className="flex items-center gap-3 px-4 py-3 hover:bg-surface-container-low/50 transition-colors"
                        style={{ borderBottom: i < 4 ? '1px solid rgba(66,71,84,0.08)' : undefined }}>
                        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                          style={{ background: PARTY_COLORS[other.party] }}>
                          {getInitials(other.name)}
                        </div>
                        <span className="text-xs text-on-surface flex-1 truncate">{other.name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${e.type === 'ally' ? 'text-blue-400' : 'text-red-400'}`}
                          style={{ background: e.type === 'ally' ? 'rgba(59,130,246,0.12)' : 'rgba(239,68,68,0.12)' }}>
                          {e.type}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Bio snippet */}
            <div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">person</span> Profile
              </h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                {selectedPolitician.bio.slice(0, 160)}...
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4" style={{ borderTop: '1px solid rgba(66,71,84,0.1)', background: '#0e0e0e' }}>
            <button onClick={() => navigate(`/politician/${selectedId}`)}
              className="w-full py-2.5 rounded-lg text-sm font-medium text-primary flex items-center justify-center gap-2 transition-colors hover:bg-surface-container-low"
              style={{ border: '1px solid rgba(173,198,255,0.25)' }}>
              View Full Entity Profile
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>
        </aside>
      ) : (
        <aside className="w-56 flex-shrink-0 flex flex-col items-center justify-center gap-3 text-center p-6"
          style={{ background: '#1c1b1b', borderLeft: '1px solid rgba(66,71,84,0.1)' }}>
          <span className="material-symbols-outlined text-on-surface-variant opacity-30" style={{ fontSize: 40 }}>
            touch_app
          </span>
          <p className="text-xs text-on-surface-variant opacity-50">
            Click a node to inspect its profile and connections
          </p>
        </aside>
      )}
    </div>
  );
}
