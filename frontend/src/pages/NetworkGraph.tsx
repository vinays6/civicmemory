import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Info, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';
import { politicians, networkEdges } from '../data/mockData';
import { Party, PARTY_COLORS } from '../types';

interface SimNode {
  id: string;
  name: string;
  party: Party;
  role: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface SimEdge {
  source: string;
  target: string;
  type: 'ally' | 'opponent';
  strength: number;
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

const REPULSION = 4500;
const SPRING_K = 0.06;
const ALLY_LENGTH = 120;
const OPP_LENGTH = 260;
const DAMPING = 0.82;
const GRAVITY = 0.025;
const NODE_RADIUS = 22;

function runStep(nodes: SimNode[], edges: SimEdge[], w: number, h: number): SimNode[] {
  const cx = w / 2;
  const cy = h / 2;
  const next = nodes.map(n => ({ ...n }));

  for (let i = 0; i < next.length; i++) {
    const n = next[i];
    let fx = 0;
    let fy = 0;

    // Repulsion between all nodes
    for (let j = 0; j < next.length; j++) {
      if (i === j) continue;
      const m = next[j];
      const dx = n.x - m.x;
      const dy = n.y - m.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = REPULSION / (dist * dist);
      fx += (dx / dist) * force;
      fy += (dy / dist) * force;
    }

    // Spring forces from edges
    for (const edge of edges) {
      const isSrc = edge.source === n.id;
      const isTgt = edge.target === n.id;
      if (!isSrc && !isTgt) continue;
      const otherId = isSrc ? edge.target : edge.source;
      const other = next.find(m => m.id === otherId);
      if (!other) continue;
      const dx = other.x - n.x;
      const dy = other.y - n.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ideal = edge.type === 'ally' ? ALLY_LENGTH : OPP_LENGTH;
      const force = SPRING_K * (dist - ideal) * edge.strength;
      fx += (dx / dist) * force;
      fy += (dy / dist) * force;
    }

    // Gravity toward center
    fx += (cx - n.x) * GRAVITY;
    fy += (cy - n.y) * GRAVITY;

    n.vx = (n.vx + fx) * DAMPING;
    n.vy = (n.vy + fy) * DAMPING;
    n.x = Math.max(NODE_RADIUS + 5, Math.min(w - NODE_RADIUS - 5, n.x + n.vx));
    n.y = Math.max(NODE_RADIUS + 5, Math.min(h - NODE_RADIUS - 5, n.y + n.vy));
  }

  return next;
}

export default function NetworkGraph() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const stepsRef = useRef(0);

  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [dims, setDims] = useState({ w: 900, h: 600 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [partyFilter, setPartyFilter] = useState<Party | 'All'>('All');
  const [zoom, setZoom] = useState(1);

  const edges: SimEdge[] = networkEdges;

  // Initialize nodes
  function initNodes(w: number, h: number): SimNode[] {
    return politicians.map((p, i) => {
      const angle = (i / politicians.length) * Math.PI * 2;
      const radius = Math.min(w, h) * 0.3;
      return {
        id: p.id,
        name: p.name,
        party: p.party,
        role: p.role,
        x: w / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: h / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      };
    });
  }

  // Measure container
  useEffect(() => {
    function measure() {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDims({ w: rect.width, h: rect.height });
      }
    }
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  // Init nodes when dims change
  useEffect(() => {
    if (dims.w > 0 && dims.h > 0) {
      setNodes(initNodes(dims.w, dims.h));
      stepsRef.current = 0;
    }
  }, [dims.w, dims.h]);

  // Run simulation
  useEffect(() => {
    if (nodes.length === 0) return;

    function tick() {
      if (stepsRef.current < 300) {
        setNodes(prev => runStep(prev, edges, dims.w, dims.h));
        stepsRef.current++;
        animRef.current = requestAnimationFrame(tick);
      }
    }

    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes.length, dims.w, dims.h]);

  function restart() {
    setNodes(initNodes(dims.w, dims.h));
    stepsRef.current = 0;
  }

  const visibleParties = partyFilter === 'All'
    ? (['Democrat', 'Republican', 'Independent', 'Libertarian', 'Green'] as Party[])
    : [partyFilter];

  const visibleNodeIds = new Set(
    nodes.filter(n => visibleParties.includes(n.party)).map(n => n.id)
  );

  const selectedPolitician = selectedId ? politicians.find(p => p.id === selectedId) : null;

  return (
    <div className="h-screen pt-16 flex flex-col bg-slate-950 overflow-hidden">
      {/* Toolbar */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-slate-800 flex items-center gap-3 flex-wrap">
        <span className="text-sm text-slate-400 font-medium">Alliance Network</span>
        <div className="h-4 w-px bg-slate-800" />

        {/* Party filters */}
        <div className="flex items-center gap-1 flex-wrap">
          {(['All', 'Democrat', 'Republican', 'Independent', 'Libertarian'] as const).map(p => (
            <button
              key={p}
              onClick={() => setPartyFilter(p as Party | 'All')}
              className={`text-xs px-3 py-1 rounded-full transition-colors border ${
                partyFilter === p
                  ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                  : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div className="ml-auto flex items-center gap-2">
          <button onClick={restart} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors" title="Restart simulation">
            <RefreshCw size={14} />
          </button>
          <button onClick={() => setZoom(z => Math.min(z + 0.2, 2))} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors">
            <ZoomIn size={14} />
          </button>
          <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.4))} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors">
            <ZoomOut size={14} />
          </button>
        </div>
      </div>

      {/* Graph + Panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* SVG canvas */}
        <div ref={containerRef} className="flex-1 relative overflow-hidden">
          <svg
            width={dims.w}
            height={dims.h}
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.2s' }}
          >
            {/* Edges */}
            <g>
              {edges.map((edge, i) => {
                const src = nodes.find(n => n.id === edge.source);
                const tgt = nodes.find(n => n.id === edge.target);
                if (!src || !tgt) return null;
                if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return null;

                const isHighlighted = hoveredId === edge.source || hoveredId === edge.target ||
                  selectedId === edge.source || selectedId === edge.target;
                const opacity = hoveredId || selectedId ? (isHighlighted ? 0.8 : 0.05) : 0.35;
                const color = edge.type === 'ally' ? '#3b82f6' : '#ef4444';
                const strokeWidth = edge.strength * 0.8;

                return (
                  <g key={i}>
                    <line
                      x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                      stroke={color}
                      strokeWidth={strokeWidth}
                      strokeOpacity={opacity}
                      strokeDasharray={edge.type === 'opponent' ? '6,4' : undefined}
                    />
                    {isHighlighted && (
                      <text
                        x={(src.x + tgt.x) / 2}
                        y={(src.y + tgt.y) / 2 - 4}
                        textAnchor="middle"
                        fill={color}
                        fontSize={10}
                        opacity={0.8}
                      >
                        {edge.type}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>

            {/* Nodes */}
            <g>
              {nodes.map(node => {
                if (!visibleNodeIds.has(node.id)) return null;
                const color = PARTY_COLORS[node.party];
                const isHovered = hoveredId === node.id;
                const isSelected = selectedId === node.id;
                const isDimmed = (hoveredId || selectedId) && !isHovered && !isSelected &&
                  !edges.some(e =>
                    (e.source === node.id && (e.target === hoveredId || e.target === selectedId)) ||
                    (e.target === node.id && (e.source === hoveredId || e.source === selectedId))
                  );

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredId(node.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => setSelectedId(prev => prev === node.id ? null : node.id)}
                  >
                    {/* Glow ring for selected */}
                    {isSelected && (
                      <circle r={NODE_RADIUS + 8} fill={color} fillOpacity={0.15} stroke={color} strokeOpacity={0.3} />
                    )}
                    {/* Hover ring */}
                    {isHovered && !isSelected && (
                      <circle r={NODE_RADIUS + 5} fill="none" stroke={color} strokeOpacity={0.4} strokeWidth={1} />
                    )}
                    {/* Main circle */}
                    <circle
                      r={NODE_RADIUS}
                      fill={color}
                      fillOpacity={isDimmed ? 0.15 : 0.85}
                      stroke={isSelected ? '#fff' : color}
                      strokeWidth={isSelected ? 2 : 1}
                      strokeOpacity={isDimmed ? 0.1 : 1}
                    />
                    {/* Initials */}
                    <text
                      textAnchor="middle"
                      dominantBaseline="central"
                      fill="#fff"
                      fillOpacity={isDimmed ? 0.2 : 1}
                      fontSize={10}
                      fontWeight={700}
                    >
                      {getInitials(node.name)}
                    </text>
                    {/* Name label */}
                    {(isHovered || isSelected) && (
                      <text
                        y={NODE_RADIUS + 14}
                        textAnchor="middle"
                        fill="#f1f5f9"
                        fontSize={11}
                        fontWeight={600}
                      >
                        {node.name.split(' ').pop()}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 p-3 rounded-lg bg-slate-900/90 backdrop-blur border border-slate-800 text-xs space-y-2">
            <p className="text-slate-400 font-medium">Connections</p>
            <div className="flex items-center gap-2 text-slate-400">
              <div className="w-8 border-t-2 border-blue-500" />
              Ally
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <div className="w-8 border-t-2 border-red-500 border-dashed" />
              Opponent
            </div>
            <p className="text-slate-500 mt-1 pt-1 border-t border-slate-800">Click node to select</p>
          </div>
        </div>

        {/* Side panel */}
        {selectedPolitician && (
          <div className="w-72 flex-shrink-0 border-l border-slate-800 bg-slate-900 overflow-y-auto p-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-300">Selected</span>
              <button
                onClick={() => setSelectedId(null)}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                ✕
              </button>
            </div>

            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold flex-shrink-0"
                style={{ backgroundColor: PARTY_COLORS[selectedPolitician.party] }}
              >
                {getInitials(selectedPolitician.name)}
              </div>
              <div>
                <p className="font-semibold text-slate-100">{selectedPolitician.name}</p>
                <p className="text-xs text-slate-500">{selectedPolitician.role} · {selectedPolitician.stateCode}</p>
              </div>
            </div>

            <div
              className="text-xs px-2.5 py-1 rounded-full inline-block font-medium"
              style={{
                backgroundColor: PARTY_COLORS[selectedPolitician.party] + '22',
                color: PARTY_COLORS[selectedPolitician.party],
              }}
            >
              {selectedPolitician.party}
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">{selectedPolitician.bio.slice(0, 180)}...</p>

            {/* Connections */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Connections</p>
              {edges
                .filter(e => e.source === selectedId || e.target === selectedId)
                .map((e, i) => {
                  const otherId = e.source === selectedId ? e.target : e.source;
                  const other = politicians.find(p => p.id === otherId);
                  if (!other) return null;
                  return (
                    <div key={i} className="flex items-center gap-2 py-1.5 border-b border-slate-800">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                        style={{ backgroundColor: PARTY_COLORS[other.party] }}
                      >
                        {getInitials(other.name)}
                      </div>
                      <span className="text-xs text-slate-300 flex-1">{other.name}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${e.type === 'ally' ? 'bg-blue-500/15 text-blue-400' : 'bg-red-500/15 text-red-400'}`}>
                        {e.type}
                      </span>
                    </div>
                  );
                })}
            </div>

            <button
              onClick={() => navigate(`/politician/${selectedId}`)}
              className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
            >
              View Full Profile
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
