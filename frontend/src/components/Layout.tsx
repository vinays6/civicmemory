import { ReactNode } from 'react';
import Navbar from './Navbar';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen text-on-surface app-backdrop grain">
      <Navbar />
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-10">{children}</main>
      <footer className="relative z-10 max-w-6xl mx-auto px-6 pb-10 pt-16">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 border-t border-outline-variant/20 pt-6">
          <div>
            <div className="wordmark text-xl leading-none text-on-surface">
              unb<em>AI</em>sed
            </div>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant">
              A dossier of the Los Angeles City Council
            </p>
          </div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant">
            Built with public records · No affiliation
          </p>
        </div>
      </footer>
    </div>
  );
}
