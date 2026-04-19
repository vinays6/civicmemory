import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Calendar, Twitter, ExternalLink, FileText, Vote, Megaphone, CalendarDays, Network } from 'lucide-react';
import { politicians, networkEdges } from '../data/mockData';
import StanceChart from '../components/StanceChart';
import PoliticianCard from '../components/PoliticianCard';
import { PARTY_COLORS } from '../types';

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

const ACTIVITY_ICONS = {
  bill: FileText,
  vote: Vote,
  statement: Megaphone,
  event: CalendarDays,
};

const ACTIVITY_COLORS = {
  bill: 'text-blue-400 bg-blue-400/10',
  vote: 'text-purple-400 bg-purple-400/10',
  statement: 'text-amber-400 bg-amber-400/10',
  event: 'text-green-400 bg-green-400/10',
};

export default function PoliticianProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const politician = politicians.find(p => p.id === id);

  if (!politician) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center text-slate-500">
        Politician not found.{' '}
        <button onClick={() => navigate('/search')} className="ml-2 text-blue-400 hover:underline">
          Search
        </button>
      </div>
    );
  }

  const color = PARTY_COLORS[politician.party];

  const allies = politician.allies
    .map(id => politicians.find(p => p.id === id))
    .filter(Boolean) as typeof politicians;

  const opponents = politician.opponents
    .map(id => politicians.find(p => p.id === id))
    .filter(Boolean) as typeof politicians;

  // Compute ideology score (simple average of stances)
  const stanceValues = Object.values(politician.stances);
  const avgScore = Math.round(stanceValues.reduce((a, b) => a + b, 0) / stanceValues.length);

  const ideologyLabel =
    avgScore < 20 ? 'Progressive' :
    avgScore < 40 ? 'Center-Left' :
    avgScore < 60 ? 'Centrist' :
    avgScore < 80 ? 'Center-Right' :
    'Conservative';

  return (
    <div className="min-h-screen bg-slate-950 pt-16">
      {/* Back */}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-slate-500 hover:text-slate-300 text-sm transition-colors mb-6"
        >
          <ArrowLeft size={14} />
          Back
        </button>
      </div>

      {/* Header */}
      <div className="max-w-6xl mx-auto px-4 mb-8">
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
          <div className="flex items-start gap-5">
            <div
              className="w-20 h-20 rounded-2xl flex items-center justify-center text-white font-bold text-2xl flex-shrink-0"
              style={{ backgroundColor: color }}
            >
              {getInitials(politician.name)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h1 className="text-2xl font-bold text-white">{politician.name}</h1>
                  <p className="text-slate-400 mt-0.5">{politician.role}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className="text-sm font-medium px-3 py-1 rounded-full"
                    style={{ backgroundColor: color + '22', color }}
                  >
                    {politician.party}
                  </span>
                  <span className="text-sm px-3 py-1 rounded-full bg-slate-800 text-slate-400">
                    {ideologyLabel}
                  </span>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-5 text-sm text-slate-500 flex-wrap">
                <span className="flex items-center gap-1.5">
                  <MapPin size={13} />
                  {politician.state}
                  {politician.district ? ` · District ${politician.district}` : ''}
                </span>
                <span className="flex items-center gap-1.5">
                  <Calendar size={13} />
                  {politician.yearsInOffice} years in office
                </span>
                <span className="text-slate-600">Age {politician.age}</span>
                {politician.twitter && (
                  <a
                    href={`https://twitter.com/${politician.twitter.replace('@', '')}`}
                    className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Twitter size={13} />
                    {politician.twitter}
                    <ExternalLink size={11} />
                  </a>
                )}
              </div>

              <div className="mt-4 flex flex-wrap gap-1.5">
                {politician.tags.map(tag => (
                  <span
                    key={tag}
                    className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Ideology meter */}
          <div className="mt-5 pt-5 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500">Overall Ideology Score</span>
              <span className="text-xs font-medium" style={{ color }}>
                {ideologyLabel} ({avgScore}/100)
              </span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${avgScore}%`,
                  background: `linear-gradient(to right, #3b82f6, #ef4444)`,
                }}
              />
            </div>
            <div className="flex justify-between mt-1 text-xs text-slate-600">
              <span>Progressive</span>
              <span>Conservative</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-4 pb-20">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Bio */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Biography</h2>
              <p className="text-slate-300 leading-relaxed text-sm">{politician.bio}</p>
            </div>

            {/* Stance Chart */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                Political Stances
              </h2>
              <StanceChart stances={politician.stances} party={politician.party} />
            </div>

            {/* Recent Activity */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                Recent Activity
              </h2>
              <div className="space-y-3">
                {politician.recentActivity.map((item, i) => {
                  const Icon = ACTIVITY_ICONS[item.type];
                  const colorClass = ACTIVITY_COLORS[item.type];
                  return (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-800">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                        <Icon size={14} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-200">{item.title}</p>
                        {item.description && (
                          <p className="text-xs text-slate-500 mt-0.5">{item.description}</p>
                        )}
                        <p className="text-xs text-slate-600 mt-1">{item.date}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ml-auto flex-shrink-0 capitalize ${colorClass}`}>
                        {item.type}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Allies */}
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Allies ({allies.length})
              </h2>
              <div className="space-y-2">
                {allies.length > 0 ? (
                  allies.map(p => (
                    <PoliticianCard key={p.id} politician={p} compact />
                  ))
                ) : (
                  <p className="text-sm text-slate-600">No allies listed</p>
                )}
              </div>
            </div>

            {/* Opponents */}
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Opponents ({opponents.length})
              </h2>
              <div className="space-y-2">
                {opponents.length > 0 ? (
                  opponents.map(p => (
                    <PoliticianCard key={p.id} politician={p} compact />
                  ))
                ) : (
                  <p className="text-sm text-slate-600">No opponents listed</p>
                )}
              </div>
            </div>

            {/* Network CTA */}
            <Link
              to="/network"
              className="flex items-center gap-3 p-5 rounded-xl bg-blue-600/10 border border-blue-600/20 hover:border-blue-600/40 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-600/20 flex items-center justify-center">
                <Network size={18} className="text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-blue-400 group-hover:text-blue-300">
                  View Alliance Network
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  See how all politicians connect
                </p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
