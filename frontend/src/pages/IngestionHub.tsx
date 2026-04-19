import { useState } from 'react';

type Tab = 'text' | 'upload' | 'agentic' | 'active';

export default function IngestionHub() {
  const [tab, setTab] = useState<Tab>('text');
  const [locality, setLocality] = useState('');
  const [date, setDate] = useState('');
  const [filterNonPolitical, setFilterNonPolitical] = useState(true);
  const [text, setText] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const tabs: { id: Tab; icon: string; label: string }[] = [
    { id: 'text',    icon: 'text_snippet', label: 'Input Text' },
    { id: 'upload',  icon: 'upload_file',  label: 'Upload Video/Audio' },
    { id: 'agentic', icon: 'psychology',   label: 'Agentic Discovery' },
    { id: 'active',  icon: 'travel_explore', label: 'Active Discovery' },
  ];

  function handleRun() {
    setIsRunning(true);
    setTimeout(() => setIsRunning(false), 3000);
  }

  return (
    <div className="h-full overflow-y-auto px-12 pb-16 pt-2">
      {/* Hero header */}
      <div className="mb-10 max-w-2xl">
        <h1 className="text-[3.25rem] leading-[1.08] font-black tracking-[-0.02em] text-on-surface mb-4">
          Analyze Local<br />Influence.
        </h1>
        <p className="text-base text-on-surface-variant leading-relaxed">
          Provide raw transcripts, meeting minutes, or direct audio recordings.
          The unbais engine will distill structural power dynamics and political leaning.
        </p>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-8 items-start">
        {/* Left: Input area */}
        <div className="col-span-8 space-y-0">
          <div className="rounded-xl overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
            style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.12)' }}>
            {/* Tab bar */}
            <div className="flex border-b overflow-x-auto" style={{ background: 'rgba(14,14,14,0.5)', borderColor: 'rgba(66,71,84,0.12)' }}>
              {tabs.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`flex items-center gap-2 px-5 py-4 text-sm font-medium transition-colors relative ${
                    tab === t.id
                      ? 'text-primary bg-surface-container-low'
                      : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">{t.icon}</span>
                  {t.label}
                  {tab === t.id && (
                    <span className="absolute bottom-0 left-0 w-full h-0.5 bg-primary" />
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="p-6">
              {tab === 'text' && (
                <div className="relative group">
                  <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Paste full transcripts, meeting minutes, or editorial text here. The unbais engine processes structural arguments and sentiment regardless of formatting..."
                    className="w-full h-96 bg-surface-container-lowest text-on-surface rounded-lg p-6 text-sm leading-relaxed resize-none focus:outline-none transition-all placeholder-on-surface-variant/30"
                    style={{ border: '1px solid rgba(66,71,84,0.2)' }}
                    onFocus={e => (e.target.style.borderColor = 'rgba(173,198,255,0.35)')}
                    onBlur={e => (e.target.style.borderColor = 'rgba(66,71,84,0.2)')}
                  />
                  <div className="absolute bottom-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-on-surface-variant hover:text-on-surface transition-colors"
                      style={{ background: 'rgba(53,53,52,0.8)', backdropFilter: 'blur(8px)', border: '1px solid rgba(66,71,84,0.2)' }}>
                      <span className="material-symbols-outlined text-[14px]">content_paste</span>
                      Paste from clipboard
                    </button>
                  </div>
                </div>
              )}

              {tab === 'upload' && (
                <div className="h-96 rounded-lg flex flex-col items-center justify-center gap-4 cursor-pointer hover:bg-surface-container/30 transition-colors"
                  style={{ border: '2px dashed rgba(66,71,84,0.3)' }}>
                  <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 48 }}>upload_file</span>
                  <div className="text-center">
                    <p className="text-sm font-medium text-on-surface">Drop files here or click to browse</p>
                    <p className="text-xs text-on-surface-variant mt-1">Supports .mp4, .mp3, .wav, .m4a, .pdf, .docx</p>
                  </div>
                  <button className="px-4 py-2 rounded-lg text-sm font-medium text-on-surface transition-colors"
                    style={{ background: '#2a2a2a', border: '1px solid rgba(66,71,84,0.3)' }}>
                    Browse files
                  </button>
                </div>
              )}

              {tab === 'agentic' && (
                <div className="h-96 rounded-lg flex flex-col items-center justify-center gap-6 relative overflow-hidden"
                  style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.12)' }}>
                  {/* Animated background */}
                  <div className="absolute inset-0 opacity-10 pointer-events-none"
                    style={{
                      background: 'linear-gradient(270deg, #3B82F6, #EF4444, #EAB308, #3B82F6)',
                      backgroundSize: '400% 400%',
                      animation: 'agenticPulse 8s ease infinite',
                    }} />
                  <span className="material-symbols-outlined text-primary z-10" style={{ fontSize: 56, fontVariationSettings: "'FILL' 1" }}>
                    smart_toy
                  </span>
                  <div className="text-center z-10">
                    <h3 className="text-xl font-bold text-on-surface mb-2">Fully Agentic Mode</h3>
                    <p className="text-sm text-on-surface-variant max-w-sm leading-relaxed">
                      The unbais agent autonomously searches for relevant local political data
                      based on your specified locality and date range.
                    </p>
                  </div>
                  <button className="z-10 px-6 py-3 rounded-lg text-sm font-bold text-on-primary transition-all hover:opacity-90"
                    style={{ background: 'linear-gradient(135deg, #adc6ff, #4d8eff)', boxShadow: '0 0 24px rgba(173,198,255,0.25)' }}>
                    <span className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px]">play_arrow</span>
                      Begin Autonomous Discovery
                    </span>
                  </button>
                </div>
              )}

              {tab === 'active' && (
                <div className="h-96 rounded-lg flex flex-col gap-4 p-6"
                  style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.12)' }}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="material-symbols-outlined text-tertiary">travel_explore</span>
                    <h3 className="text-base font-bold text-on-surface">Active Discovery URLs</h3>
                  </div>
                  <p className="text-sm text-on-surface-variant">Provide URLs for the agent to actively monitor and extract political data from.</p>
                  <div className="flex gap-2">
                    <input type="url" placeholder="https://citycouncil.gov/minutes..." className="flex-1 bg-surface-container-lowest px-4 py-2.5 rounded-lg text-sm text-on-surface placeholder-on-surface-variant/40 focus:outline-none"
                      style={{ border: '1px solid rgba(66,71,84,0.2)' }} />
                    <button className="px-4 py-2.5 rounded-lg text-sm font-medium text-on-primary"
                      style={{ background: '#adc6ff' }}>
                      Add
                    </button>
                  </div>
                  <div className="flex-1 rounded-lg p-4 flex items-center justify-center"
                    style={{ border: '1px dashed rgba(66,71,84,0.25)' }}>
                    <p className="text-xs text-on-surface-variant">No URLs added yet</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Config */}
        <div className="col-span-4 space-y-5">
          {/* Context Parameters */}
          <div className="rounded-xl p-6 shadow-[0_8px_32px_rgba(0,0,0,0.3)]"
            style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.12)' }}>
            <h2 className="text-base font-bold text-on-surface mb-5 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
              Context Parameters
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                  Locality Name
                </label>
                <input
                  type="text"
                  value={locality}
                  onChange={e => setLocality(e.target.value)}
                  placeholder="e.g. City Council of Seattle"
                  className="w-full bg-surface-container-lowest px-4 py-3 rounded-lg text-sm text-on-surface placeholder-on-surface-variant/40 focus:outline-none transition-all"
                  style={{ border: '1px solid rgba(66,71,84,0.2)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(173,198,255,0.4)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(66,71,84,0.2)')}
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                  Meeting Date
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={date}
                    onChange={e => setDate(e.target.value)}
                    className="w-full bg-surface-container-lowest px-4 py-3 rounded-lg text-sm text-on-surface focus:outline-none transition-all appearance-none"
                    style={{ border: '1px solid rgba(66,71,84,0.2)', colorScheme: 'dark' }}
                    onFocus={e => (e.target.style.borderColor = 'rgba(173,198,255,0.4)')}
                    onBlur={e => (e.target.style.borderColor = 'rgba(66,71,84,0.2)')}
                  />
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-[18px]">
                    calendar_today
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Extraction Filters */}
          <div className="rounded-xl p-6 shadow-[0_8px_32px_rgba(0,0,0,0.2)]"
            style={{ background: '#1c1b1b', border: '1px solid rgba(66,71,84,0.12)' }}>
            <h2 className="text-base font-bold text-on-surface mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary text-[20px]">filter_alt</span>
              Extraction Filters
            </h2>
            <div className="flex items-start justify-between gap-4 p-4 rounded-lg"
              style={{ background: 'rgba(14,14,14,0.5)', border: '1px solid rgba(66,71,84,0.08)' }}>
              <div>
                <p className="text-sm font-semibold text-on-surface">Identify Non-Political Conflicts</p>
                <p className="text-xs text-on-surface-variant mt-1 leading-snug">
                  Filter out personal gripes or administrative friction from ideological scoring.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer flex-shrink-0 mt-0.5">
                <input
                  type="checkbox"
                  checked={filterNonPolitical}
                  onChange={e => setFilterNonPolitical(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 rounded-full peer transition-colors peer-checked:bg-primary bg-surface-variant"
                  style={{ border: '1px solid rgba(66,71,84,0.2)' }}>
                  <div className={`absolute top-[3px] left-[3px] w-[18px] h-[18px] bg-white rounded-full transition-transform duration-200 ${filterNonPolitical ? 'translate-x-5' : ''}`} />
                </div>
              </label>
            </div>
          </div>

          {/* CTA */}
          <div className="relative pt-1">
            <div className="absolute inset-x-4 top-2 h-12 blur-2xl opacity-40 pointer-events-none rounded-full"
              style={{ background: 'linear-gradient(90deg, #adc6ff, #4d8eff)' }} />
            <button
              onClick={handleRun}
              disabled={isRunning}
              className="w-full relative overflow-hidden group rounded-xl py-4 px-6 font-bold text-base text-on-primary transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-70 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, #adc6ff, #4d8eff)',
                boxShadow: '0 4px 14px rgba(173,198,255,0.25)',
              }}
            >
              <div className="flex items-center justify-center gap-3 relative z-10">
                <span className="material-symbols-outlined text-[22px]">
                  {isRunning ? 'hourglass_top' : 'memory'}
                </span>
                {isRunning ? "Processing..." : "Run 'unbais' Analysis"}
              </div>
              {!isRunning && (
                <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
              )}
            </button>
            <div className="flex items-center justify-center gap-2 mt-3 text-xs text-on-surface-variant">
              <span className="material-symbols-outlined text-primary/70 text-[14px]" style={{ animation: 'pulse 2s infinite' }}>
                check_circle
              </span>
              System ready · Est. processing time ~45s
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
