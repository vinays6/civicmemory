import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { MemberSummary } from '../api/types';
import { Card, ErrorBox, Skeleton, TallyBar } from '../components/ui';

export default function MembersIndex() {
  const [members, setMembers] = useState<MemberSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listMembers()
      .then(setMembers)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  const totals = useMemo(() => {
    if (!members) return null;
    let meetings = 0;
    let votes = 0;
    let stances = 0;
    for (const m of members) {
      meetings = Math.max(meetings, m.meeting_count);
      votes += m.vote_counts.aye + m.vote_counts.nay + m.vote_counts.absent;
      stances += m.opinion_topic_count;
    }
    return { members: members.length, meetings, votes, stances };
  }, [members]);

  return (
    <div className="relative">
      {/* Editorial masthead */}
      <header className="relative mb-12">
        <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.28em] text-on-surface-variant">
          <span className="h-px w-8 bg-primary/60" />
          <span>Dossier № 01</span>
          <span className="text-outline-variant/80">/</span>
          <span>Los Angeles City Council</span>
        </div>

        <h1 className="mt-5 font-display font-medium text-on-surface leading-[0.95] tracking-tight text-[64px] sm:text-[80px]">
          The council,
          <br />
          <span className="italic text-primary/90" style={{ fontVariationSettings: "'SOFT' 80, 'opsz' 120" }}>
            unb<span className="not-italic text-on-surface">·</span>AI<span className="not-italic text-on-surface">·</span>sed
          </span>
          <span className="text-on-surface">.</span>
        </h1>

        <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-on-surface-variant">
          Voting records, recorded stances, and issue-level predictions for every
          member — assembled from public meetings and read back without the spin.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-4">
          <Stat label="Members" value={totals?.members} />
          <Stat label="Meetings covered" value={totals?.meetings} />
          <Stat label="Votes cast" value={totals?.votes} />
          <Stat label="Recorded stances" value={totals?.stances} />

          <Link
            to="/network"
            className="ml-auto group inline-flex items-center gap-3 rounded-full border border-primary/30 bg-primary/10 px-5 py-2.5 text-primary hover:bg-primary/15 hover:border-primary/50 transition-colors"
          >
            <span className="font-mono text-[11px] uppercase tracking-[0.22em]">
              Voting network
            </span>
            <span className="text-base leading-none transition-transform group-hover:translate-x-0.5">
              →
            </span>
          </Link>
        </div>
      </header>

      {error && <ErrorBox message={error} />}

      {!members && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      )}

      {members && (
        <>
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.26em] text-on-surface-variant">
              <span>The roster</span>
              <span className="h-px w-16 bg-outline-variant/40" />
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant tabular-nums">
              {String(members.length).padStart(2, '0')} profiles
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {members.map((m, i) => (
              <Link
                key={m.name}
                to={`/members/${encodeURIComponent(m.name)}`}
                className="group"
              >
                <Card className="p-5 h-full transition-all duration-200 group-hover:border-primary/40 group-hover:-translate-y-0.5 group-hover:shadow-editorial-hover">
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant tabular-nums mt-1">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant tabular-nums">
                      {m.meeting_count} mtgs
                    </span>
                  </div>

                  <h2 className="mt-1 font-display text-[26px] leading-[1.05] tracking-tight text-on-surface truncate">
                    {m.name}
                  </h2>

                  <div className="mt-5">
                    <TallyBar counts={m.vote_counts} />
                    <div className="mt-2 flex gap-4 font-mono text-[11px] text-on-surface-variant tabular-nums">
                      <span>
                        <span className="text-emerald-300">{m.vote_counts.aye}</span> aye
                      </span>
                      <span>
                        <span className="text-rose-300">{m.vote_counts.nay}</span> nay
                      </span>
                      <span>
                        <span className="text-slate-400">{m.vote_counts.absent}</span> abs
                      </span>
                    </div>
                  </div>

                  <div className="mt-5">
                    <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant mb-2">
                      Speaks on
                    </div>
                    {m.issues.length === 0 ? (
                      <span className="text-xs text-on-surface-variant">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {m.issues.slice(0, 4).map((issue) => (
                          <span
                            key={issue}
                            className="text-[11px] px-2 py-0.5 rounded-full border border-outline-variant/30 text-on-surface-variant group-hover:border-outline-variant/60 transition-colors"
                          >
                            {issue}
                          </span>
                        ))}
                        {m.issues.length > 4 && (
                          <span className="text-[11px] px-2 py-0.5 text-on-surface-variant">
                            +{m.issues.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div>
      <div className="font-display text-[28px] leading-none tracking-tight text-on-surface tabular-nums">
        {value === undefined ? '—' : value.toLocaleString()}
      </div>
      <div className="mt-1.5 font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant">
        {label}
      </div>
    </div>
  );
}
