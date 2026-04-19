import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { api, ApiError } from '../../api/client';
import type { MemberVote, Position } from '../../api/types';
import { Card, ErrorBox, PositionBadge, Skeleton } from '../ui';

const POSITIONS: ('all' | Position)[] = ['all', 'aye', 'nay', 'absent'];

export default function VotesTab({ name }: { name: string }) {
  const [votes, setVotes] = useState<MemberVote[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | Position>('all');
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setVotes(null);
    setError(null);
    api
      .getMemberVotes(name)
      .then(setVotes)
      .catch((e: ApiError) => setError(e.message));
  }, [name]);

  const described = useMemo(
    () => (votes ?? []).filter((v) => v.description && v.description.trim().length > 0),
    [votes]
  );

  const filtered = useMemo(() => {
    const sorted = [...described].sort((a, b) =>
      b.meeting_date.localeCompare(a.meeting_date)
    );
    const byPosition =
      filter === 'all' ? sorted : sorted.filter((v) => v.position === filter);
    const q = query.trim().toLowerCase();
    if (!q) return byPosition;
    return byPosition.filter(
      (v) =>
        v.description.toLowerCase().includes(q) ||
        v.file_code.toLowerCase().includes(q) ||
        v.disposition?.toLowerCase().includes(q)
    );
  }, [described, filter, query]);

  if (error) return <ErrorBox message={error} />;
  if (!votes) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {POSITIONS.map((p) => (
          <button
            key={p}
            onClick={() => setFilter(p)}
            className={`text-xs uppercase tracking-widest px-3 py-1.5 rounded border transition-colors ${
              filter === p
                ? 'border-primary/50 bg-primary/10 text-primary'
                : 'border-outline-variant/30 text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {p === 'all'
              ? `all (${described.length})`
              : `${p} (${described.filter((v) => v.position === p).length})`}
          </button>
        ))}

        <div className="relative flex-1 min-w-[220px] ml-auto">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search description, file code, disposition…"
            className="w-full bg-surface-container-low border border-outline-variant/30 focus:border-primary/50 focus:outline-none rounded-lg pl-9 pr-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/60"
          />
        </div>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-widest text-on-surface-variant border-b border-outline-variant/20">
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Item</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Disposition</th>
              <th className="px-4 py-3 font-medium">Vote</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((v, i) => {
              const key = `${v.meeting_date}-${v.item_number}-${i}`;
              const isOpen = expanded === key;
              return (
                <tr
                  key={key}
                  onClick={() => setExpanded(isOpen ? null : key)}
                  className="border-b border-outline-variant/10 hover:bg-surface-container-low/50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-on-surface-variant tabular-nums whitespace-nowrap">
                    {v.meeting_date}
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant whitespace-nowrap">
                    #{v.item_number}
                    <span className="ml-2 text-[10px] text-on-surface-variant/70">
                      {v.file_code}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-on-surface max-w-md">
                    <div className={isOpen ? '' : 'truncate'}>
                      {v.description || '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant whitespace-nowrap">
                    {v.disposition || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <PositionBadge position={v.position} />
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-10 text-center text-on-surface-variant text-sm"
                >
                  No votes match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
