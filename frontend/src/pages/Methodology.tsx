const SPECTRUM = [
  { label: 'Progressive', color: '#3B82F6', glow: 'rgba(59,130,246,0.4)' },
  { label: 'Swing / Centrist', color: '#EAB308', glow: 'rgba(234,179,8,0.4)' },
  { label: 'Conservative', color: '#EF4444', glow: 'rgba(239,68,68,0.4)' },
  { label: 'Administrative', color: '#6B7280', glow: 'transparent', dim: true },
];

export default function Methodology() {
  return (
    <div className="h-full overflow-y-auto px-12 pb-24 pt-2">
      {/* Page header */}
      <div className="mt-6 mb-16 max-w-4xl">
        <p className="text-primary text-[11px] font-bold uppercase tracking-widest mb-4 flex items-center gap-2">
          <span className="w-8 h-px bg-primary block" />
          Core Philosophy
        </p>
        <h1 className="text-[3.25rem] leading-[1.06] font-black tracking-[-0.02em] text-on-surface mb-6">
          How 'unbais' Analyzes<br />Local Rhetoric
        </h1>
        <p className="text-lg text-on-surface-variant leading-relaxed max-w-2xl">
          Transparency is the foundation of editorial intelligence. Our architecture is designed
          to dissect unstructured civic data with profound neutrality.
        </p>
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-12 gap-x-8 gap-y-10 max-w-5xl">
        {/* Section 1: Local gap */}
        <div className="col-span-7 rounded-xl p-10 relative overflow-hidden group transition-colors duration-500 hover:bg-surface-container-low"
          style={{ background: '#0e0e0e' }}>
          <div className="absolute top-0 right-0 w-28 h-28 rounded-bl-full opacity-20 pointer-events-none"
            style={{ background: '#353534', marginRight: -32, marginTop: -32 }} />
          <span className="material-symbols-outlined text-primary mb-6 block" style={{ fontSize: 32 }}>satellite_alt</span>
          <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-4">
            Filling Local Training Gaps
          </h2>
          <div className="space-y-4 text-[0.95rem] leading-relaxed text-on-surface-variant">
            <p>
              Foundation models are overwhelmingly trained on national discourse, federal legislature,
              and mass-market journalism. When tasked with analyzing local municipality data — city
              council meeting minutes, zoning board transcripts, local ordinances — these models often
              hallucinate national partisan framing onto hyper-local issues.
            </p>
            <p>
              <strong className="text-on-surface">unbais</strong> addresses this by deploying specialized
              ingestion pipelines that normalize unstructured civic transcripts before analysis begins,
              establishing a baseline vocabulary that respects the nuance of local governance without
              relying on pre-packaged national narratives.
            </p>
          </div>
        </div>

        {/* Abstract visual */}
        <div className="col-span-5 rounded-xl relative overflow-hidden flex items-center justify-center"
          style={{ background: '#0e0e0e', border: '1px solid rgba(66,71,84,0.12)', minHeight: 240 }}>
          <div className="absolute inset-0 opacity-8"
            style={{ background: 'radial-gradient(ellipse at center, rgba(173,198,255,0.08) 0%, transparent 70%)' }} />
          <div className="relative w-28 h-28 rounded-full flex items-center justify-center"
            style={{ border: '1px solid rgba(173,198,255,0.2)', boxShadow: '0 0 40px rgba(173,198,255,0.05)' }}>
            <div className="w-14 h-14 rounded-full"
              style={{ background: 'rgba(173,198,255,0.08)', border: '1px solid rgba(173,198,255,0.35)' }} />
          </div>
        </div>

        {/* Section 2: Cognitive separation */}
        <div className="col-span-12 rounded-xl p-10 lg:p-12 relative overflow-hidden"
          style={{ background: '#1c1b1b', boxShadow: '0 24px 48px -12px rgba(0,0,0,0.5)' }}>
          <div className="absolute inset-0 pointer-events-none rounded-xl"
            style={{ background: 'linear-gradient(135deg, rgba(173,198,255,0.04) 0%, transparent 60%)' }} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 relative">
            <div>
              <span className="material-symbols-outlined text-secondary mb-6 block" style={{ fontSize: 32 }}>psychology</span>
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-4">
                Cognitive Separation Framework
              </h2>
              <p className="text-on-surface-variant text-[0.95rem] leading-relaxed mb-5">
                The core of our methodology utilizes <strong className="text-on-surface">Claude's advanced
                reasoning capabilities</strong> to perform a strict semantic bifurcation of text.
                We instruct the model to rigorously separate language into two distinct channels:
              </p>
              <p className="text-[11px] text-primary font-bold uppercase tracking-widest mb-2">
                The Dual-Channel Approach
              </p>
              <div className="h-px w-10 rounded-full bg-primary/30 mb-5" />
            </div>

            <div className="flex flex-col justify-center gap-4">
              <div className="p-6 rounded-lg transition-colors hover:border-on-surface-variant/30"
                style={{ background: '#201f1f', border: '1px solid rgba(66,71,84,0.2)' }}>
                <h3 className="text-base font-semibold text-on-surface mb-2 flex items-center gap-2">
                  <span className="material-symbols-outlined text-on-surface-variant text-[16px]">corporate_fare</span>
                  Administrative Execution
                </h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">
                  Language strictly concerning logistical operations, budget allocations, procedural
                  motions, and raw governance mechanics. Classified as neutral civic function.
                </p>
              </div>
              <div className="p-6 rounded-lg transition-colors hover:border-on-surface-variant/30"
                style={{ background: '#201f1f', border: '1px solid rgba(66,71,84,0.2)' }}>
                <h3 className="text-base font-semibold text-on-surface mb-2 flex items-center gap-2">
                  <span className="material-symbols-outlined text-tertiary text-[16px]">campaign</span>
                  Ideological Signaling
                </h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">
                  Language that embeds values, moral posturing, partisan talking points, or cultural
                  identifiers into the administrative process. Isolated for vector mapping.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Vector proximity */}
        <div className="col-span-8 rounded-xl p-10" style={{ background: '#0e0e0e' }}>
          <span className="material-symbols-outlined text-tertiary mb-6 block" style={{ fontSize: 32 }}>scatter_plot</span>
          <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-4">
            Vector Proximity Determination
          </h2>
          <div className="space-y-4 text-[0.95rem] leading-relaxed text-on-surface-variant">
            <p>
              Once ideological signaling is isolated, the text is mapped into a high-dimensional
              vector space. Rather than relying on simple keyword matching, we calculate the semantic
              proximity of the rhetoric against established centroids.
            </p>
            <p>
              The final classification is not binary, but a spectrum mapping based on geometric
              distance within the vector space, allowing us to accurately categorize rhetoric into
              distinct analytical bands.
            </p>
          </div>
        </div>

        {/* Spectrum visual */}
        <div className="col-span-4 rounded-xl p-8 flex flex-col justify-center" style={{ background: '#0e0e0e' }}>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-6">
            Classification Spectrum
          </h4>
          <div className="space-y-4">
            {SPECTRUM.map(({ label, color, glow, dim }, i) => (
              <div key={label}>
                <div className={`flex items-center justify-between ${dim ? 'opacity-50' : ''}`}>
                  <span className="text-sm font-medium text-on-surface">{label}</span>
                  <div className="w-4 h-4 rounded-full" style={{ background: color, boxShadow: `0 0 12px ${glow}` }} />
                </div>
                {i < SPECTRUM.length - 1 && (
                  <div className="w-full h-px mt-4" style={{ background: 'rgba(66,71,84,0.2)' }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="col-span-12 mt-4 p-8 rounded-xl flex items-center justify-between gap-8"
          style={{ background: 'linear-gradient(135deg, rgba(173,198,255,0.06), rgba(77,142,255,0.04))', border: '1px solid rgba(173,198,255,0.1)' }}>
          <div>
            <h3 className="text-lg font-bold text-on-surface mb-1">Ready to analyze your local district?</h3>
            <p className="text-sm text-on-surface-variant">
              Submit a transcript or enable agentic discovery for your region.
            </p>
          </div>
          <a href="/" className="flex-shrink-0 px-6 py-3 rounded-lg font-bold text-sm text-on-primary transition-all hover:opacity-90 hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #adc6ff, #4d8eff)', boxShadow: '0 4px 14px rgba(173,198,255,0.2)' }}>
            Start Analysis
          </a>
        </div>
      </div>
    </div>
  );
}
