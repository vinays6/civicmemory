import { Link } from 'react-router-dom';
import { MapPin, Calendar } from 'lucide-react';
import { Politician, PARTY_COLORS } from '../types';

interface Props {
  politician: Politician;
  compact?: boolean;
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

export default function PoliticianCard({ politician, compact = false }: Props) {
  const color = PARTY_COLORS[politician.party];

  if (compact) {
    return (
      <Link
        to={`/politician/${politician.id}`}
        className="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-600 transition-all group"
      >
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
          style={{ backgroundColor: color }}
        >
          {getInitials(politician.name)}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate group-hover:text-white">
            {politician.name}
          </p>
          <p className="text-xs text-slate-500 truncate">
            {politician.role} · {politician.stateCode}
          </p>
        </div>
        <div
          className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: color }}
        />
      </Link>
    );
  }

  return (
    <Link
      to={`/politician/${politician.id}`}
      className="block p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-600 transition-all group hover:shadow-lg hover:shadow-black/20"
    >
      <div className="flex items-start gap-4">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-base flex-shrink-0"
          style={{ backgroundColor: color }}
        >
          {getInitials(politician.name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-base font-semibold text-slate-100 group-hover:text-white">
                {politician.name}
              </h3>
              <p className="text-sm text-slate-400">{politician.role}</p>
            </div>
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: color + '22', color }}
            >
              {politician.party}
            </span>
          </div>

          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <MapPin size={11} />
              {politician.state}
            </span>
            <span className="flex items-center gap-1">
              <Calendar size={11} />
              {politician.yearsInOffice}y in office
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-1">
            {politician.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700"
              >
                #{tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Stance bar preview */}
      <div className="mt-4 space-y-1.5">
        {(['climate', 'economy', 'immigration'] as const).map(issue => (
          <div key={issue} className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 capitalize">{issue}</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${politician.stances[issue]}%`,
                  backgroundColor: politician.stances[issue] < 50 ? '#3b82f6' : '#ef4444',
                }}
              />
            </div>
            <span className="text-xs text-slate-600 w-6 text-right">
              {politician.stances[issue]}
            </span>
          </div>
        ))}
      </div>
    </Link>
  );
}
