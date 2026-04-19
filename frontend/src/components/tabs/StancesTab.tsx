import { useEffect, useMemo, useState } from 'react';
import { Play, Sparkles } from 'lucide-react';

function parseYoutubeSeconds(url: string): number | null {
  const m = url.match(/[?&]t=([^&]+)/);
  if (!m) return null;
  const raw = m[1];
  if (/^\d+$/.test(raw)) return parseInt(raw, 10);
  if (/^\d+s$/.test(raw)) return parseInt(raw, 10);
  // Handles forms like 1h2m30s, 5m, 90s
  let total = 0;
  const re = /(\d+)([hms])/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(raw)) !== null) {
    const n = parseInt(match[1], 10);
    if (match[2] === 'h') total += n * 3600;
    else if (match[2] === 'm') total += n * 60;
    else total += n;
  }
  return total || null;
}

function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}
import { api, ApiError } from '../../api/client';
import type { MemberOpinion, MemberProfileEnvelope } from '../../api/types';
import { Card, ConfidenceBar, EmptyState, ErrorBox, Pct, SentimentBadge, Skeleton } from '../ui';

export default function StancesTab({ name }: { name: string }) {
  const [opinions, setOpinions] = useState<MemberOpinion[] | null>(null);
  const [profile, setProfile] = useState<MemberProfileEnvelope | null>(null);
  const [profileMissing, setProfileMissing] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setOpinions(null);
    setProfile(null);
    setProfileMissing(false);
    setError(null);

    api.getMemberOpinions(name).then(setOpinions).catch((e: ApiError) => setError(e.message));

    api
      .getMemberProfile(name)
      .then(setProfile)
      .catch((e: ApiError) => {
        if (e.status === 404) setProfileMissing(true);
        else setError(e.message);
      });
  }, [name]);

  const grouped = useMemo(() => {
    if (!opinions) return [];
    const byIssue = new Map<string, MemberOpinion[]>();
    for (const op of opinions) {
      const list = byIssue.get(op.issue) ?? [];
      list.push(op);
      byIssue.set(op.issue, list);
    }
    return [...byIssue.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [opinions]);

  async function onBuildProfile() {
    setBuilding(true);
    setError(null);
    try {
      await api.buildMemberProfile(name);
      const env = await api.getMemberProfile(name);
      setProfile(env);
      setProfileMissing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBuilding(false);
    }
  }

  if (error) return <ErrorBox message={error} />;

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
              <Sparkles size={14} className="text-primary" />
              Synthesized political profile
            </h3>
            <p className="text-xs text-on-surface-variant mt-1">
              Aggregated across every meeting using the Member Memory agent.
            </p>
          </div>
          {profileMissing && (
            <button
              onClick={onBuildProfile}
              disabled={building}
              className="text-xs px-3 py-1.5 rounded border border-primary/40 bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-60"
            >
              {building ? 'Building…' : 'Build profile'}
            </button>
          )}
        </div>

        <div className="mt-4">
          {!profile && !profileMissing && <Skeleton className="h-24 w-full" />}
          {profileMissing && !profile && (
            <EmptyState message="No synthesized profile yet. Build one to see themes, commitments, and ideology dimensions." />
          )}
          {profile && <ProfileDetails profile={profile} />}
        </div>
      </Card>

      <div>
        <h3 className="text-sm font-semibold text-on-surface mb-3">
          Recorded stances by issue
        </h3>
        {!opinions && <Skeleton className="h-40" />}
        {opinions && grouped.length === 0 && (
          <EmptyState message="No recorded stances for this member yet." />
        )}
        <div className="space-y-4">
          {grouped.map(([issue, items]) => (
            <Card key={issue} className="p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h4 className="text-base font-semibold text-on-surface">{issue}</h4>
                <span className="text-[10px] uppercase tracking-widest text-on-surface-variant">
                  {items.length} remark{items.length === 1 ? '' : 's'}
                </span>
              </div>
              <ul className="space-y-3">
                {items.map((op, i) => (
                  <li
                    key={`${op.meeting_date}-${i}`}
                    className="border-l-2 border-outline-variant/30 pl-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <SentimentBadge sentiment={op.sentiment} />
                      <span className="text-xs text-on-surface-variant tabular-nums">
                        {op.meeting_date}
                      </span>
                    </div>
                    <div className="text-sm text-on-surface">{op.stance}</div>
                    {op.youtube_links.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {op.youtube_links.map((url, j) => {
                          const secs = parseYoutubeSeconds(url);
                          const label = secs != null ? formatTimestamp(secs) : `Clip ${j + 1}`;
                          return (
                            <a
                              key={url + j}
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              title="Open clip on YouTube"
                              className="group/ts inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/[0.07] pl-1.5 pr-2.5 py-[3px] text-primary transition-all duration-150 hover:border-primary/60 hover:bg-primary/[0.14] hover:shadow-[0_0_0_3px_rgba(173,198,255,0.08)]"
                            >
                              <span className="flex items-center justify-center w-4 h-4 rounded-full bg-primary/20 group-hover/ts:bg-primary/30 transition-colors">
                                <Play size={8} className="fill-primary text-primary translate-x-[0.5px]" />
                              </span>
                              <span className="font-mono text-[10.5px] tabular-nums tracking-wider">
                                {label}
                              </span>
                            </a>
                          );
                        })}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProfileDetails({ profile: envelope }: { profile: MemberProfileEnvelope }) {
  const p = envelope.profile;
  const issues = Object.entries(p.issue_positions);
  return (
    <div className="space-y-4">
      {p.themes.length > 0 && (
        <Row label="Themes">
          <div className="flex flex-wrap gap-1.5">
            {p.themes.map((t) => (
              <Chip key={t}>{t}</Chip>
            ))}
          </div>
        </Row>
      )}
      {p.ideology_dimensions.length > 0 && (
        <Row label="Ideology">
          <div className="flex flex-wrap gap-1.5">
            {p.ideology_dimensions.map((t) => (
              <Chip key={t}>{t}</Chip>
            ))}
          </div>
        </Row>
      )}
      {p.recurring_issues.length > 0 && (
        <Row label="Recurring issues">
          <div className="flex flex-wrap gap-1.5">
            {p.recurring_issues.map((t) => (
              <Chip key={t}>{t}</Chip>
            ))}
          </div>
        </Row>
      )}
      <Row label="Commitment reliability">
        <div className="flex items-center gap-3">
          <div className="w-32">
            <ConfidenceBar value={p.commitment_reliability} />
          </div>
          <span className="text-xs text-on-surface-variant tabular-nums">
            <Pct value={p.commitment_reliability} />
          </span>
        </div>
      </Row>
      {issues.length > 0 && (
        <Row label="Positions">
          <ul className="space-y-2">
            {issues.map(([issue, pos]) => (
              <li key={issue} className="text-sm">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-on-surface font-medium">{issue}</span>
                  <span className="text-[11px] text-on-surface-variant tabular-nums">
                    <Pct value={pos.confidence} /> confident
                  </span>
                </div>
                <div className="text-xs text-on-surface-variant mt-0.5">{pos.stance}</div>
              </li>
            ))}
          </ul>
        </Row>
      )}
      {envelope.updated_at && (
        <div className="text-[10px] text-on-surface-variant/70 pt-1 border-t border-outline-variant/20">
          Updated {new Date(envelope.updated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-4 items-start">
      <span className="text-[10px] uppercase tracking-widest text-on-surface-variant pt-0.5">
        {label}
      </span>
      <div>{children}</div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[11px] px-2 py-0.5 rounded border border-outline-variant/30 text-on-surface">
      {children}
    </span>
  );
}
