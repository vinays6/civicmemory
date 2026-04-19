import { ReactNode } from 'react';
import type { Sentiment, Position, PredictedVote } from '../api/types';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`relative rounded-xl bg-surface-container-low/80 border border-outline-variant/25 shadow-editorial backdrop-blur-[2px] ${className}`}
    >
      {/* Top inner hairline for a subtle lit edge */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"
      />
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant mb-2">
        {label}
      </div>
      <div className="font-display text-3xl leading-none tracking-tight text-on-surface tabular-nums">
        {value}
      </div>
      {sub !== undefined && (
        <div className="text-xs text-on-surface-variant mt-2">{sub}</div>
      )}
    </Card>
  );
}

export function Pct({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined || Number.isNaN(value)) return <>—</>;
  return <>{(value * 100).toFixed(1)}%</>;
}

const sentimentStyle: Record<Sentiment, string> = {
  positive: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  negative: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  neutral: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  mixed: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
};

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span
      className={`inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${sentimentStyle[sentiment]}`}
    >
      {sentiment}
    </span>
  );
}

const positionStyle: Record<Position, string> = {
  aye: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  nay: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  absent: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};

export function PositionBadge({ position }: { position: Position }) {
  return (
    <span
      className={`inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${positionStyle[position]}`}
    >
      {position}
    </span>
  );
}

const predictedStyle: Record<PredictedVote, string> = {
  yes: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  no: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  abstain: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  unclear: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
};

export function PredictedBadge({ vote }: { vote: PredictedVote }) {
  return (
    <span
      className={`inline-block text-xs uppercase tracking-wider px-2.5 py-1 rounded border font-medium ${predictedStyle[vote]}`}
    >
      {vote}
    </span>
  );
}

export function TallyBar({
  counts,
}: {
  counts: { aye: number; nay: number; absent: number };
}) {
  const total = counts.aye + counts.nay + counts.absent;
  if (total === 0) return <div className="h-2 rounded bg-surface-container-high" />;
  const pct = (n: number) => (n / total) * 100;
  return (
    <div className="h-2 w-full rounded overflow-hidden flex bg-surface-container-high">
      <div style={{ width: `${pct(counts.aye)}%` }} className="bg-emerald-500/70" />
      <div style={{ width: `${pct(counts.nay)}%` }} className="bg-rose-500/70" />
      <div style={{ width: `${pct(counts.absent)}%` }} className="bg-slate-500/40" />
    </div>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="h-1.5 w-full rounded bg-surface-container-high overflow-hidden">
      <div
        className="h-full bg-primary/70"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton-shimmer rounded-lg ${className}`} />;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-200 px-4 py-3 text-sm">
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-outline-variant/30 bg-surface-container-low/50 text-on-surface-variant px-4 py-6 text-sm text-center">
      {message}
    </div>
  );
}
