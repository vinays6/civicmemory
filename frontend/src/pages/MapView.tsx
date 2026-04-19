import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps';
import { X, ChevronRight, MapPin, Users } from 'lucide-react';
import { politicians } from '../data/mockData';
import { Politician, PARTY_COLORS, Party } from '../types';
import PoliticianCard from '../components/PoliticianCard';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

const PARTY_FILTERS: (Party | 'All')[] = ['All', 'Democrat', 'Republican', 'Independent', 'Libertarian', 'Green'];

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2);
}

export default function MapView() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Politician | null>(null);
  const [partyFilter, setPartyFilter] = useState<Party | 'All'>('All');

  const filtered = partyFilter === 'All'
    ? politicians
    : politicians.filter(p => p.party === partyFilter);

  return (
    <div className="h-screen pt-16 flex flex-col bg-slate-950">
      {/* Toolbar */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-slate-800 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1.5 text-sm text-slate-400">
          <MapPin size={14} />
          <span>US Political Map</span>
        </div>
        <div className="h-4 w-px bg-slate-800" />
        <div className="flex items-center gap-1 flex-wrap">
          {PARTY_FILTERS.map(p => (
            <button
              key={p}
              onClick={() => setPartyFilter(p as Party | 'All')}
              className={`text-xs px-3 py-1 rounded-full transition-colors border ${
                partyFilter === p
                  ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                  : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
          <Users size={12} />
          {filtered.length} politicians shown
        </div>
      </div>

      {/* Map + Sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="flex-1 relative bg-slate-950">
          <ComposableMap
            projection="geoAlbersUsa"
            style={{ width: '100%', height: '100%' }}
          >
            <ZoomableGroup>
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map(geo => (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      style={{
                        default: { fill: '#0f172a', stroke: '#1e293b', strokeWidth: 0.5, outline: 'none' },
                        hover: { fill: '#1e293b', stroke: '#334155', strokeWidth: 0.5, outline: 'none' },
                        pressed: { fill: '#1e293b', outline: 'none' },
                      }}
                    />
                  ))
                }
              </Geographies>

              {filtered.map(politician => {
                const color = PARTY_COLORS[politician.party];
                const isSelected = selected?.id === politician.id;
                return (
                  <Marker
                    key={politician.id}
                    coordinates={[politician.lng, politician.lat]}
                    onClick={() => setSelected(isSelected ? null : politician)}
                  >
                    <g style={{ cursor: 'pointer' }}>
                      {isSelected && (
                        <circle
                          r={22}
                          fill={color}
                          fillOpacity={0.15}
                          stroke={color}
                          strokeOpacity={0.3}
                          strokeWidth={1}
                        />
                      )}
                      <circle
                        r={isSelected ? 14 : 10}
                        fill={color}
                        fillOpacity={0.9}
                        stroke="#020617"
                        strokeWidth={isSelected ? 2 : 1.5}
                        style={{ transition: 'all 0.2s' }}
                      />
                      <text
                        textAnchor="middle"
                        dominantBaseline="central"
                        style={{ fontSize: isSelected ? 7 : 6, fill: '#fff', fontWeight: 700, userSelect: 'none' }}
                      >
                        {getInitials(politician.name)}
                      </text>
                    </g>
                  </Marker>
                );
              })}
            </ZoomableGroup>
          </ComposableMap>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 p-3 rounded-lg bg-slate-900/90 backdrop-blur border border-slate-800 text-xs space-y-1.5">
            <p className="text-slate-400 font-medium mb-2">Legend</p>
            {(['Democrat', 'Republican', 'Independent', 'Libertarian'] as Party[]).map(p => (
              <div key={p} className="flex items-center gap-2 text-slate-400">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: PARTY_COLORS[p] }} />
                {p}
              </div>
            ))}
          </div>

          {/* Tip */}
          {!selected && (
            <div className="absolute top-4 right-4 px-3 py-2 rounded-lg bg-slate-900/90 backdrop-blur border border-slate-800 text-xs text-slate-500">
              Click a marker to see politician info
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-80 flex-shrink-0 border-l border-slate-800 bg-slate-900 overflow-y-auto flex flex-col">
          {selected ? (
            <div className="flex flex-col h-full">
              {/* Selected politician header */}
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-300">Selected</span>
                <button
                  onClick={() => setSelected(null)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="p-4">
                <PoliticianCard politician={selected} />
                <button
                  onClick={() => navigate(`/politician/${selected.id}`)}
                  className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                >
                  Full Profile
                  <ChevronRight size={14} />
                </button>
              </div>

              <div className="px-4 pb-2 pt-1">
                <div className="h-px bg-slate-800" />
                <p className="text-xs text-slate-500 mt-3 mb-2">Also in {selected.stateCode}</p>
              </div>
              <div className="px-4 pb-4 space-y-2">
                {politicians
                  .filter(p => p.stateCode === selected.stateCode && p.id !== selected.id)
                  .map(p => (
                    <PoliticianCard key={p.id} politician={p} compact />
                  ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-slate-800">
                <p className="text-sm font-medium text-slate-300">All Politicians</p>
                <p className="text-xs text-slate-500 mt-0.5">{filtered.length} shown</p>
              </div>
              <div className="p-3 space-y-2 overflow-y-auto">
                {filtered.map(p => (
                  <PoliticianCard
                    key={p.id}
                    politician={p}
                    compact
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
