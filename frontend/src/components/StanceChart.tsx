import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Stances, PARTY_COLORS, Party } from '../types';

interface Props {
  stances: Stances;
  party: Party;
}

const ISSUE_LABELS: Record<keyof Stances, string> = {
  healthcare: 'Healthcare',
  economy: 'Economy',
  climate: 'Climate',
  immigration: 'Immigration',
  education: 'Education',
  defense: 'Defense',
};

const ISSUE_DESCRIPTIONS: Record<keyof Stances, { low: string; high: string }> = {
  healthcare: { low: 'Universal', high: 'Private Market' },
  economy: { low: 'Regulated', high: 'Free Market' },
  climate: { low: 'Aggressive Action', high: 'Skeptical' },
  immigration: { low: 'Open Policy', high: 'Strict Enforcement' },
  education: { low: 'Public / Free', high: 'School Choice' },
  defense: { low: 'Reduce Spending', high: 'Increase Spending' },
};

export default function StanceChart({ stances, party }: Props) {
  const color = PARTY_COLORS[party];

  const data = (Object.keys(stances) as Array<keyof Stances>).map(key => ({
    subject: ISSUE_LABELS[key],
    value: stances[key],
    fullMark: 100,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="#1e293b" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 500 }}
          />
          <Radar
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.15}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: 8,
              color: '#f1f5f9',
              fontSize: 12,
            }}
            formatter={(value: number, name: string, props) => {
              const issue = (Object.keys(ISSUE_LABELS) as Array<keyof Stances>).find(
                k => ISSUE_LABELS[k] === props.payload.subject
              );
              if (!issue) return [value, name];
              const desc = ISSUE_DESCRIPTIONS[issue];
              const label = value < 50 ? desc.low : desc.high;
              return [`${value}/100 — ${label}`, props.payload.subject];
            }}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Legend bar */}
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500 px-2">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
          Liberal / Progressive
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
          Conservative
        </span>
      </div>

      {/* Issue breakdown */}
      <div className="mt-4 space-y-2">
        {(Object.keys(stances) as Array<keyof Stances>).map(key => {
          const value = stances[key];
          const desc = ISSUE_DESCRIPTIONS[key];
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-24 capitalize">{ISSUE_LABELS[key]}</span>
              <div className="flex-1 relative h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="absolute left-0 top-0 h-full rounded-full"
                  style={{
                    width: `${value}%`,
                    backgroundColor: value < 50 ? '#3b82f6' : '#ef4444',
                    opacity: 0.8,
                  }}
                />
              </div>
              <span className="text-xs text-slate-500 w-32 text-right">
                {value < 35 ? desc.low : value > 65 ? desc.high : 'Moderate'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
