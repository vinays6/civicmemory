import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, SlidersHorizontal, X } from 'lucide-react';
import { politicians } from '../data/mockData';
import { Party, PARTY_COLORS } from '../types';
import PoliticianCard from '../components/PoliticianCard';

const PARTIES: Party[] = ['Democrat', 'Republican', 'Independent', 'Green', 'Libertarian'];
const ROLES = ['President', 'Vice President', 'Senator', 'Representative', 'Governor', 'Secretary', 'Mayor', 'Ambassador'];
const ISSUES = ['healthcare', 'economy', 'climate', 'immigration', 'education', 'defense'] as const;

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [selectedParties, setSelectedParties] = useState<Party[]>([]);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'yearsInOffice'>('name');
  const [issueRange, setIssueRange] = useState<{ issue: typeof ISSUES[number]; min: number; max: number } | null>(null);

  // Sync query with URL
  useEffect(() => {
    const q = searchParams.get('q');
    if (q) setQuery(q);
  }, [searchParams]);

  const results = useMemo(() => {
    let list = politicians;

    // Text search
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(p =>
        p.name.toLowerCase().includes(q) ||
        p.state.toLowerCase().includes(q) ||
        p.stateCode.toLowerCase().includes(q) ||
        p.role.toLowerCase().includes(q) ||
        p.party.toLowerCase().includes(q) ||
        p.tags.some(t => t.toLowerCase().includes(q)) ||
        p.bio.toLowerCase().includes(q)
      );
    }

    // Party filter
    if (selectedParties.length > 0) {
      list = list.filter(p => selectedParties.includes(p.party));
    }

    // Role filter
    if (selectedRoles.length > 0) {
      list = list.filter(p => selectedRoles.includes(p.role));
    }

    // Issue range filter
    if (issueRange) {
      list = list.filter(p => {
        const v = p.stances[issueRange.issue];
        return v >= issueRange.min && v <= issueRange.max;
      });
    }

    // Sort
    if (sortBy === 'name') {
      list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    } else {
      list = [...list].sort((a, b) => b.yearsInOffice - a.yearsInOffice);
    }

    return list;
  }, [query, selectedParties, selectedRoles, sortBy, issueRange]);

  function toggleParty(p: Party) {
    setSelectedParties(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  }

  function toggleRole(r: string) {
    setSelectedRoles(prev =>
      prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]
    );
  }

  function clearFilters() {
    setQuery('');
    setSelectedParties([]);
    setSelectedRoles([]);
    setIssueRange(null);
  }

  const activeFilterCount = selectedParties.length + selectedRoles.length + (issueRange ? 1 : 0);

  return (
    <div className="min-h-screen bg-slate-950 pt-24 pb-20">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Browse Politicians</h1>
          <p className="text-slate-500 text-sm mt-1">
            Search and filter across all tracked political figures
          </p>
        </div>

        {/* Search bar */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <SearchIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name, state, party, issue..."
              value={query}
              onChange={e => {
                setQuery(e.target.value);
                setSearchParams(e.target.value ? { q: e.target.value } : {});
              }}
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
            />
            {query && (
              <button
                onClick={() => { setQuery(''); setSearchParams({}); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <X size={14} />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-sm font-medium transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                : 'border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-600'
            }`}
          >
            <SlidersHorizontal size={14} />
            Filters
            {activeFilterCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as 'name' | 'yearsInOffice')}
            className="px-4 py-3 rounded-xl border border-slate-700 bg-slate-900 text-slate-400 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="name">Sort: Name</option>
            <option value="yearsInOffice">Sort: Experience</option>
          </select>
        </div>

        {/* Filter panel */}
        {showFilters && (
          <div className="mb-6 p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-300">Filters</span>
              {activeFilterCount > 0 && (
                <button onClick={clearFilters} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                  Clear all
                </button>
              )}
            </div>

            {/* Party */}
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Party</p>
              <div className="flex flex-wrap gap-2">
                {PARTIES.map(p => {
                  const active = selectedParties.includes(p);
                  const color = PARTY_COLORS[p];
                  return (
                    <button
                      key={p}
                      onClick={() => toggleParty(p)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-all`}
                      style={{
                        borderColor: active ? color : '#334155',
                        backgroundColor: active ? color + '22' : 'transparent',
                        color: active ? color : '#94a3b8',
                      }}
                    >
                      {p}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Role */}
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Role</p>
              <div className="flex flex-wrap gap-2">
                {ROLES.map(r => {
                  const active = selectedRoles.includes(r);
                  return (
                    <button
                      key={r}
                      onClick={() => toggleRole(r)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                        active
                          ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                          : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                      }`}
                    >
                      {r}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Issue stance filter */}
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Filter by Stance</p>
              <div className="flex flex-wrap gap-2">
                {ISSUES.map(issue => {
                  const active = issueRange?.issue === issue;
                  return (
                    <button
                      key={issue}
                      onClick={() => setIssueRange(active ? null : { issue, min: 0, max: 50 })}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-colors capitalize ${
                        active
                          ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                          : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                      }`}
                    >
                      {issue} (liberal)
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-600 mt-1">Click an issue to show politicians with a liberal stance (score &lt; 50)</p>
            </div>
          </div>
        )}

        {/* Results */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-slate-500">
            {results.length} result{results.length !== 1 ? 's' : ''}
            {query ? ` for "${query}"` : ''}
          </span>
          {(query || activeFilterCount > 0) && (
            <button onClick={clearFilters} className="text-xs text-blue-400 hover:text-blue-300">
              Clear
            </button>
          )}
        </div>

        {results.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {results.map(p => (
              <PoliticianCard key={p.id} politician={p} />
            ))}
          </div>
        ) : (
          <div className="text-center py-20 text-slate-600">
            <SearchIcon size={40} className="mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium text-slate-500">No results found</p>
            <p className="text-sm mt-1">Try adjusting your search or filters</p>
            <button onClick={clearFilters} className="mt-4 text-blue-400 hover:text-blue-300 text-sm">
              Clear all filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
