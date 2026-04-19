import { useState } from 'react';
import { Sparkles, Send } from 'lucide-react';
import { api, ApiError } from '../../api/client';
import type { VotePrediction } from '../../api/types';
import { Card, ConfidenceBar, ErrorBox, Pct, PredictedBadge, Skeleton } from '../ui';

interface Turn {
  issue: string;
  prediction: VotePrediction;
}

export default function PredictTab({ name }: { name: string }) {
  const [issue, setIssue] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = issue.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const prediction = await api.predictVote(q, name);
      setTurns((prev) => [{ issue: q, prediction }, ...prev]);
      setIssue('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
          <Sparkles size={14} className="text-primary" />
          Predict {name}'s vote
        </h3>
        <p className="text-xs text-on-surface-variant mt-1">
          Describe a hypothetical motion or policy. The prediction agent reasons from this
          member's prior votes, campaign platform, and finance summary.
        </p>
        <form onSubmit={submit} className="mt-4 flex gap-2">
          <input
            value={issue}
            onChange={(e) => setIssue(e.target.value)}
            placeholder="e.g. Expand rent stabilization to cover units built after 1978"
            className="flex-1 bg-surface-container-low border border-outline-variant/40 focus:border-primary/60 focus:outline-none rounded-lg px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/60"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !issue.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary/20 border border-primary/40 text-primary hover:bg-primary/30 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            <Send size={13} />
            {loading ? 'Predicting…' : 'Predict'}
          </button>
        </form>
        {error && (
          <div className="mt-3">
            <ErrorBox message={error} />
          </div>
        )}
        {loading && (
          <div className="mt-4">
            <Skeleton className="h-32" />
          </div>
        )}
      </Card>

      {turns.map((turn, i) => (
        <PredictionTurn key={i} turn={turn} />
      ))}

      {turns.length === 0 && !loading && (
        <div className="text-center text-xs text-on-surface-variant py-8">
          No predictions yet — ask a question above.
        </div>
      )}
    </div>
  );
}

function PredictionTurn({ turn }: { turn: Turn }) {
  const p = turn.prediction;
  return (
    <Card className="p-5">
      <div className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1">
        Issue
      </div>
      <div className="text-sm text-on-surface mb-5">{turn.issue}</div>

      <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="text-sm font-semibold text-on-surface">{p.member_name}</div>
          <PredictedBadge vote={p.predicted_vote} />
        </div>
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1">
            <ConfidenceBar value={p.confidence} />
          </div>
          <span className="text-xs text-on-surface-variant tabular-nums">
            <Pct value={p.confidence} /> confident
          </span>
        </div>
        <p className="text-sm text-on-surface-variant leading-relaxed">{p.reasoning}</p>
        {p.evidence_meetings.length > 0 && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1.5">
              Evidence
            </div>
            <div className="flex flex-wrap gap-1.5">
              {p.evidence_meetings.map((ev) => (
                <span
                  key={ev}
                  className="text-[10px] px-2 py-0.5 rounded border border-outline-variant/30 text-on-surface-variant tabular-nums"
                >
                  {ev}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
