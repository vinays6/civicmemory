import { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

const BREADCRUMBS: Record<string, { parent: string; current: string }> = {
  '/':            { parent: 'Platform', current: 'Ingestion' },
  '/network':     { parent: 'Analysis', current: 'Network' },
  '/entities':    { parent: 'Database', current: 'Explorer' },
  '/methodology': { parent: 'Platform', current: 'Transparency' },
};

interface Props {
  children: ReactNode;
}

export default function Layout({ children }: Props) {
  const { pathname } = useLocation();
  const crumb = BREADCRUMBS[pathname] ?? { parent: 'Platform', current: 'Page' };

  return (
    <div className="flex h-screen bg-surface text-on-surface overflow-hidden">
      <Sidebar />

      <div className="ml-64 flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="flex-shrink-0 flex items-center justify-between px-12 py-5 z-40"
          style={{ background: 'transparent' }}>
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest">
            <span className="text-on-surface-variant">{crumb.parent}</span>
            <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 14 }}>
              chevron_right
            </span>
            <span className="text-primary border-b-2 border-primary pb-0.5">{crumb.current}</span>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-5">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: 16 }}>
                search
              </span>
              <input
                type="text"
                placeholder="Search entities..."
                className="bg-surface-container-low pl-9 pr-4 py-2 rounded-full text-xs text-on-surface placeholder-on-surface-variant/50 focus:outline-none w-52 transition-all"
                style={{ border: '1px solid rgba(66,71,84,0.25)' }}
                onFocus={e => (e.target.style.borderColor = 'rgba(173,198,255,0.4)')}
                onBlur={e => (e.target.style.borderColor = 'rgba(66,71,84,0.25)')}
              />
            </div>
            <div className="flex items-center gap-3 text-on-surface-variant">
              <button className="hover:text-on-surface transition-colors relative">
                <span className="material-symbols-outlined">notifications</span>
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-secondary border border-surface" />
              </button>
              <button className="hover:text-on-surface transition-colors">
                <span className="material-symbols-outlined">history</span>
              </button>
              <button className="hover:text-on-surface transition-colors">
                <span className="material-symbols-outlined">account_circle</span>
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
