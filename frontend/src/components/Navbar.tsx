import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const { pathname } = useLocation();
  const onHome = pathname === '/';
  return (
    <nav className="sticky top-0 z-40 border-b border-outline-variant/30 bg-surface/70 backdrop-blur-xl">
      {/* hairline top accent */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-baseline gap-3 group">
          <span className="wordmark text-[26px] leading-none text-on-surface">
            unb<em>AI</em>sed
          </span>
          <span className="hidden sm:inline-block h-5 w-px bg-outline-variant/40 translate-y-0.5" />
          <span className="hidden sm:inline-block font-mono text-[10px] uppercase tracking-[0.22em] text-on-surface-variant translate-y-0.5">
            Council Intelligence
          </span>
        </Link>

        <div className="flex items-center gap-5">
          <Link
            to="/network"
            className="hidden sm:inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <span className="w-1 h-1 rounded-full bg-primary/70" />
            Network
          </Link>
          {!onHome && (
            <Link
              to="/"
              className="font-mono text-[11px] uppercase tracking-[0.18em] text-on-surface-variant hover:text-on-surface transition-colors"
            >
              ← Index
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
