import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { MemberStats, MemberSummary } from '../api/types';
import { Card, ErrorBox, Skeleton, TallyBar } from '../components/ui';
import OverviewTab from '../components/tabs/OverviewTab';
import VotesTab from '../components/tabs/VotesTab';
import StancesTab from '../components/tabs/StancesTab';
import PredictTab from '../components/tabs/PredictTab';

type Tab = 'overview' | 'votes' | 'stances' | 'predict';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'votes', label: 'Votes' },
  { id: 'stances', label: 'Stances' },
  { id: 'predict', label: 'Predict' },
];

export default function MemberProfile() {
  const { name: rawName } = useParams();
  const name = useMemo(() => (rawName ? decodeURIComponent(rawName) : ''), [rawName]);

  const [summary, setSummary] = useState<MemberSummary | null>(null);
  const [stats, setStats] = useState<MemberStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    setSummary(null);
    setStats(null);
    setError(null);

    Promise.all([
      api.listMembers().then((list) => list.find((m) => m.name === name) ?? null),
      api.getMemberStats(name).catch((e: ApiError) => {
        if (e.status === 400) return null;
        throw e;
      }),
    ])
      .then(([s, st]) => {
        if (cancelled) return;
        setSummary(s);
        setStats(st);
      })
      .catch((e: ApiError) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (!name) return <ErrorBox message="Invalid member name in URL." />;
  if (error) return <ErrorBox message={error} />;

  return (
    <div>
      <header className="mb-6">
        {summary ? (
          <div>
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.28em] text-on-surface-variant">
              <span className="h-px w-6 bg-primary/60" />
              <span>Member profile</span>
            </div>
            <h1 className="mt-3 font-display font-medium text-on-surface leading-[0.95] tracking-tight text-[52px] sm:text-[64px]">
              {summary.name}
              <span className="text-primary/80">.</span>
            </h1>
            <div className="mt-4 flex items-center gap-6 font-mono text-[11px] uppercase tracking-[0.18em] text-on-surface-variant tabular-nums">
              <span>{summary.meeting_count} meetings</span>
              <span className="text-outline-variant/70">·</span>
              <span>{summary.opinion_topic_count} stances</span>
              <span className="text-outline-variant/70">·</span>
              <span>
                {summary.vote_counts.aye + summary.vote_counts.nay} votes
              </span>
            </div>
            <div className="mt-4 max-w-md">
              <TallyBar counts={summary.vote_counts} />
            </div>
          </div>
        ) : (
          <Skeleton className="h-24 w-full max-w-md" />
        )}
      </header>

      <div className="border-b border-outline-variant/30 mb-6">
        <nav className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.22em] border-b-2 transition-colors -mb-px ${
                tab === t.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'overview' && (
        <OverviewTab name={name} summary={summary} stats={stats} />
      )}
      {tab === 'votes' && <VotesTab name={name} />}
      {tab === 'stances' && <StancesTab name={name} />}
      {tab === 'predict' && <PredictTab name={name} />}
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <Card className="p-6">
      <Skeleton className="h-4 w-32 mb-3" />
      <Skeleton className="h-8 w-64" />
    </Card>
  );
}
