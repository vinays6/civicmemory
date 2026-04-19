import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { VotingNetwork as Network, VotingNetworkEdge } from '../api/types';
import { Card, ErrorBox, Skeleton } from '../components/ui';

const BLOC_COLORS: Record<number, string> = {
  1: '#fb7185', // rose
  2: '#60a5fa', // blue
  3: '#fbbf24', // amber
  4: '#34d399', // emerald
  5: '#c084fc', // violet
};

// Slightly hotter core color used in the node radial gradient.
const BLOC_CORE: Record<number, string> = {
  1: '#ffd4dc',
  2: '#cfe3ff',
  3: '#fff1c2',
  4: '#c9f5e3',
  5: '#e7d5ff',
};

const DEFAULT_COLOR = '#9ca3af';
const DEFAULT_CORE = '#e5e7eb';

function colorFor(bloc: number) {
  return BLOC_COLORS[bloc] ?? DEFAULT_COLOR;
}
function coreFor(bloc: number) {
  return BLOC_CORE[bloc] ?? DEFAULT_CORE;
}

const WIDTH = 800;
const HEIGHT = 560;

type NodePos = { name: string; x: number; y: number; vx: number; vy: number };

const REPULSION = 9000;
const CENTER_PULL = 0.01;
const SPRING_BASE = 0.03;

// One-shot force-directed layout.
function settle(nodes: NodePos[], edges: VotingNetworkEdge[], iterations = 400) {
  const idx = new Map(nodes.map((n, i) => [n.name, i]));
  const cx = WIDTH / 2;
  const cy = HEIGHT / 2;

  for (let step = 0; step < iterations; step++) {
    const cooling = 1 - step / iterations;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist2 = Math.max(dx * dx + dy * dy, 100);
        const force = REPULSION / dist2;
        const dist = Math.sqrt(dist2);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }
    for (const e of edges) {
      const ia = idx.get(e.a);
      const ib = idx.get(e.b);
      if (ia === undefined || ib === undefined) continue;
      const a = nodes[ia];
      const b = nodes[ib];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const targetDist = 80 + (1 - e.rate) * 320;
      const diff = dist - targetDist;
      const strength = SPRING_BASE * (0.3 + e.rate * 0.7);
      const fx = (dx / dist) * diff * strength;
      const fy = (dy / dist) * diff * strength;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }
    for (const n of nodes) {
      n.vx += (cx - n.x) * CENTER_PULL;
      n.vy += (cy - n.y) * CENTER_PULL;
      n.vx *= 0.7 * cooling + 0.15;
      n.vy *= 0.7 * cooling + 0.15;
      n.x += n.vx;
      n.y += n.vy;
      n.x = Math.max(40, Math.min(WIDTH - 40, n.x));
      n.y = Math.max(40, Math.min(HEIGHT - 40, n.y));
    }
  }
  return nodes;
}

export default function VotingNetworkPage() {
  const [network, setNetwork] = useState<Network | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0);
  const [hovered, setHovered] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .votingNetwork({ k: 3 })
      .then(setNetwork)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  const nodes = useMemo(() => {
    if (!network) return [];
    const n = network.members.length;
    const radius = 200;
    const cx = WIDTH / 2;
    const cy = HEIGHT / 2;
    const initial: NodePos[] = network.members.map((name, i) => ({
      name,
      x: cx + Math.cos((2 * Math.PI * i) / n) * radius,
      y: cy + Math.sin((2 * Math.PI * i) / n) * radius,
      vx: 0,
      vy: 0,
    }));
    return settle(initial, network.edges);
  }, [network]);

  const positions = useMemo(() => {
    const map = new Map<string, NodePos>();
    for (const n of nodes) map.set(n.name, n);
    return map;
  }, [nodes]);

  const visibleEdges = useMemo(
    () => (network?.edges ?? []).filter((e) => e.rate >= threshold),
    [network, threshold]
  );

  if (error) return <ErrorBox message={error} />;

  return (
    <div>
      <header className="mb-8 flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.28em] text-on-surface-variant">
            <span className="h-px w-6 bg-primary/60" />
            <span>Dossier № 02</span>
            <span className="text-outline-variant/80">/</span>
            <span>The voting network</span>
          </div>
          <h1 className="mt-3 font-display font-medium text-on-surface leading-[0.95] tracking-tight text-[44px] sm:text-[56px]">
            Who votes
            <span className="italic text-primary/90"> with</span> whom
            <span className="text-primary/80">.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-on-surface-variant">
            Each member is a node. Links connect members by how often they voted
            the same way on <strong className="text-on-surface font-medium">contested</strong> items.
            Distance ≈ disagreement; color ≈ bloc.
          </p>
        </div>
        <Link
          to="/"
          className="font-mono text-[11px] uppercase tracking-[0.22em] text-on-surface-variant hover:text-on-surface transition-colors whitespace-nowrap"
        >
          ← Index
        </Link>
      </header>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-4 mb-3">
          <label className="flex items-center gap-2 text-xs text-on-surface-variant">
            <span className="uppercase tracking-widest">Min agreement</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-primary"
            />
            <span className="tabular-nums text-on-surface w-10">
              {(threshold * 100).toFixed(0)}%
            </span>
          </label>
          {network && (
            <span className="text-xs text-on-surface-variant ml-auto">
              {visibleEdges.length} / {network.edges.length} edges shown
            </span>
          )}
        </div>

        {!network && <Skeleton className="h-[560px]" />}

        {network && (
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="w-full h-[560px] rounded-lg"
            style={{
              background:
                'radial-gradient(ellipse at 50% 40%, #1a1d2b 0%, #0c0e16 70%, #07080d 100%)',
            }}
          >
            <defs>
              <pattern
                id="vn-grid"
                width="32"
                height="32"
                patternUnits="userSpaceOnUse"
              >
                <circle cx="1" cy="1" r="1" fill="#ffffff" fillOpacity="0.04" />
              </pattern>
              <radialGradient id="vn-vignette" cx="50%" cy="45%" r="65%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="0.04" />
                <stop offset="100%" stopColor="#000000" stopOpacity="0" />
              </radialGradient>
              <filter id="vn-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="vn-edge-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="1.4" />
              </filter>
              {[0, 1, 2, 3, 4, 5].map((bloc) => (
                <radialGradient
                  key={`node-grad-${bloc}`}
                  id={`vn-node-${bloc}`}
                  cx="35%"
                  cy="30%"
                  r="70%"
                >
                  <stop offset="0%" stopColor={coreFor(bloc)} stopOpacity="1" />
                  <stop offset="55%" stopColor={colorFor(bloc)} stopOpacity="1" />
                  <stop offset="100%" stopColor={colorFor(bloc)} stopOpacity="0.9" />
                </radialGradient>
              ))}
              {/* One linear gradient per ordered bloc pair for two-tone edges. */}
              {[0, 1, 2, 3, 4, 5].flatMap((ba) =>
                [0, 1, 2, 3, 4, 5].map((bb) => (
                  <linearGradient
                    key={`edge-${ba}-${bb}`}
                    id={`vn-edge-${ba}-${bb}`}
                    gradientUnits="userSpaceOnUse"
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="0"
                  >
                    <stop offset="0%" stopColor={colorFor(ba)} />
                    <stop offset="100%" stopColor={colorFor(bb)} />
                  </linearGradient>
                ))
              )}
            </defs>

            {/* Backdrop */}
            <rect width={WIDTH} height={HEIGHT} fill="url(#vn-grid)" />
            <rect width={WIDTH} height={HEIGHT} fill="url(#vn-vignette)" />

            {/* Edges (curved, gradient-stroked, with soft glow layer) */}
            <g filter="url(#vn-edge-glow)" opacity={0.55}>
              {visibleEdges.map((e) => {
                const a = positions.get(e.a);
                const b = positions.get(e.b);
                if (!a || !b) return null;
                const isHighlighted =
                  hovered && (hovered === e.a || hovered === e.b);
                if (!isHighlighted && hovered) return null;
                const mx = (a.x + b.x) / 2;
                const my = (a.y + b.y) / 2;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const len = Math.sqrt(dx * dx + dy * dy) || 1;
                const nx = -dy / len;
                const ny = dx / len;
                const curve = Math.min(40, len * 0.12);
                const cxp = mx + nx * curve;
                const cyp = my + ny * curve;
                const ba = network.blocs[e.a] ?? 0;
                const bb = network.blocs[e.b] ?? 0;
                return (
                  <path
                    key={`glow-${e.a}|${e.b}`}
                    d={`M ${a.x} ${a.y} Q ${cxp} ${cyp} ${b.x} ${b.y}`}
                    fill="none"
                    stroke={`url(#vn-edge-${ba}-${bb})`}
                    strokeOpacity={e.rate * 0.9}
                    strokeWidth={Math.max(1.2, e.rate * 3.2)}
                    strokeLinecap="round"
                  />
                );
              })}
            </g>
            <g>
              {visibleEdges.map((e) => {
                const a = positions.get(e.a);
                const b = positions.get(e.b);
                if (!a || !b) return null;
                const isHighlighted =
                  hovered && (hovered === e.a || hovered === e.b);
                const dim = hovered && !isHighlighted;
                const mx = (a.x + b.x) / 2;
                const my = (a.y + b.y) / 2;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const len = Math.sqrt(dx * dx + dy * dy) || 1;
                const nx = -dy / len;
                const ny = dx / len;
                const curve = Math.min(40, len * 0.12);
                const cxp = mx + nx * curve;
                const cyp = my + ny * curve;
                const ba = network.blocs[e.a] ?? 0;
                const bb = network.blocs[e.b] ?? 0;
                const stroke = isHighlighted
                  ? '#e5e2e1'
                  : `url(#vn-edge-${ba}-${bb})`;
                return (
                  <path
                    key={`${e.a}|${e.b}`}
                    d={`M ${a.x} ${a.y} Q ${cxp} ${cyp} ${b.x} ${b.y}`}
                    fill="none"
                    stroke={stroke}
                    strokeOpacity={
                      dim ? 0.04 : isHighlighted ? 0.95 : e.rate * 0.55
                    }
                    strokeWidth={
                      isHighlighted ? 2.2 : Math.max(0.6, e.rate * 1.6)
                    }
                    strokeLinecap="round"
                  />
                );
              })}
            </g>

            {/* Nodes */}
            <g>
              {nodes.map((n) => {
                const bloc = network.blocs[n.name] ?? 0;
                const color = colorFor(bloc);
                const isHover = hovered === n.name;
                const dim = hovered && !isHover;
                const r = isHover ? 18 : 13;
                return (
                  <g
                    key={n.name}
                    onMouseEnter={() => setHovered(n.name)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() =>
                      navigate(`/members/${encodeURIComponent(n.name)}`)
                    }
                    style={{ cursor: 'pointer' }}
                    opacity={dim ? 0.35 : 1}
                  >
                    {/* Outer glow halo */}
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r={isHover ? 36 : 26}
                      fill={color}
                      fillOpacity={isHover ? 0.25 : 0.12}
                      filter="url(#vn-glow)"
                    />
                    {/* Inner hover ring */}
                    {isHover && (
                      <circle
                        cx={n.x}
                        cy={n.y}
                        r={r + 4}
                        fill="none"
                        stroke={color}
                        strokeOpacity={0.7}
                        strokeWidth={1}
                      />
                    )}
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r={r}
                      fill={`url(#vn-node-${bloc})`}
                      stroke="#0b0c12"
                      strokeWidth={1.5}
                    />
                    {/* Specular highlight */}
                    <circle
                      cx={n.x - r * 0.3}
                      cy={n.y - r * 0.35}
                      r={r * 0.35}
                      fill="#ffffff"
                      fillOpacity={0.35}
                      style={{ pointerEvents: 'none' }}
                    />
                    <text
                      x={n.x}
                      y={n.y - r - 6}
                      fontSize={isHover ? 13 : 11}
                      textAnchor="middle"
                      fill={isHover ? '#f5f3f2' : '#aab0c4'}
                      fontWeight={isHover ? 600 : 500}
                      style={{
                        pointerEvents: 'none',
                        letterSpacing: '0.01em',
                        paintOrder: 'stroke',
                        stroke: '#07080d',
                        strokeWidth: 3,
                        strokeLinejoin: 'round',
                      }}
                    >
                      {n.name}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        )}

        {network && (
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-on-surface-variant">
            {[...new Set(Object.values(network.blocs))].sort().map((bloc) => {
              const members = Object.entries(network.blocs)
                .filter(([, b]) => b === bloc)
                .map(([m]) => m);
              const color = colorFor(bloc);
              return (
                <div
                  key={bloc}
                  className="flex items-center gap-2 rounded-full px-3 py-1 border border-white/5 bg-white/[0.02]"
                >
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: color,
                      boxShadow: `0 0 8px ${color}`,
                    }}
                  />
                  <span className="text-on-surface font-medium">Bloc {bloc}</span>
                  <span className="tabular-nums">{members.length}</span>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
