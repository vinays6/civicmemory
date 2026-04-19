import type { MemberStats, MemberSummary } from '../../api/types';
import { Card, Pct, Skeleton, StatCard } from '../ui';

interface Props {
  name: string;
  summary: MemberSummary | null;
  stats: MemberStats | null;
}

export default function OverviewTab({ summary, stats }: Props) {
  if (!summary || !stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  const alignment = Object.entries(stats.alignment_row_contested)
    .filter((entry): entry is [string, number] => typeof entry[1] === 'number')
    .sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Aye rate"
          value={<Pct value={stats.aye_rate} />}
          sub="when present"
        />
        <StatCard
          label="Participation"
          value={<Pct value={stats.participation_rate} />}
          sub={`${stats.vote_counts.aye + stats.vote_counts.nay} of ${
            stats.vote_counts.aye + stats.vote_counts.nay + stats.vote_counts.absent
          }`}
        />
        <StatCard
          label="Dissent rate"
          value={<Pct value={stats.dissent_rate} />}
          sub="votes against majority"
        />
        <StatCard
          label="Kingmaker score"
          value={stats.kingmaker.score}
          sub="items this vote flipped"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-on-surface mb-4">
            Top co-dissent partners
          </h3>
          {stats.top_codissent_partners.length === 0 ? (
            <div className="text-sm text-on-surface-variant">
              No significant co-dissent partners.
            </div>
          ) : (
            <ul className="space-y-3">
              {stats.top_codissent_partners.map((p) => (
                <li
                  key={p.member}
                  className="flex items-center justify-between gap-3"
                >
                  <span className="text-sm text-on-surface">{p.member}</span>
                  <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                    <span>n={p.n}</span>
                    <span className="text-on-surface tabular-nums">
                      <Pct value={p.rate} />
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold text-on-surface mb-4">
            Alignment on contested votes
          </h3>
          {alignment.length === 0 ? (
            <div className="text-sm text-on-surface-variant">
              No overlapping contested votes.
            </div>
          ) : (
            <ul className="space-y-2">
              {alignment.map(([other, rate]) => (
                <li key={other} className="flex items-center gap-3">
                  <span className="text-sm text-on-surface w-32 truncate">{other}</span>
                  <div className="flex-1 h-1.5 rounded bg-surface-container-high overflow-hidden">
                    <div
                      className="h-full bg-primary/60"
                      style={{ width: `${rate * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-on-surface-variant w-12 text-right tabular-nums">
                    <Pct value={rate} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {stats.lone_wolf_items.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-on-surface mb-1">Lone-wolf votes</h3>
          <p className="text-xs text-on-surface-variant mb-3">
            Items where this member was the only aye or the only nay on the floor.
          </p>
          <div className="text-sm text-on-surface-variant">
            {stats.lone_wolf_items.length} item{stats.lone_wolf_items.length === 1 ? '' : 's'}
          </div>
        </Card>
      )}
    </div>
  );
}
