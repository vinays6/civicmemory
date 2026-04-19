import { NavLink, useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/',           icon: 'input',         label: 'Ingestion Hub',     end: true },
  { to: '/network',    icon: 'hub',           label: 'Network Dashboard', end: false },
  { to: '/entities',   icon: 'manage_search', label: 'Entity Explorer',   end: false },
  { to: '/methodology',icon: 'description',   label: 'Methodology',       end: false },
];

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 z-50 flex flex-col p-6 space-y-8"
      style={{ background: 'rgba(28,27,27,0.85)', backdropFilter: 'blur(20px)' }}>

      {/* Brand */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded flex items-center justify-center font-black text-sm text-on-primary shadow-lg"
            style={{ background: 'linear-gradient(135deg, #adc6ff, #4d8eff)' }}>
            u
          </div>
          <h1 className="text-2xl font-black tracking-tighter leading-none text-on-surface">
            unbais<span className="text-primary">.</span>
          </h1>
        </div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant opacity-60 pl-9">
          Editorial Intelligence
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 py-3 px-4 rounded-lg text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-surface-container-highest text-primary font-bold'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className="material-symbols-outlined text-[20px]"
                  style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
                >
                  {icon}
                </span>
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* CTA + Footer */}
      <div className="space-y-4">
        <button
          onClick={() => navigate('/')}
          className="w-full py-3 px-4 rounded-lg font-bold text-sm text-on-primary flex items-center justify-center gap-2 transition-all duration-200 hover:opacity-90 hover:-translate-y-0.5 shadow-lg"
          style={{
            background: 'linear-gradient(135deg, #adc6ff, #4d8eff)',
            boxShadow: '0 4px 14px rgba(173,198,255,0.2), inset 0 1px 0 rgba(255,255,255,0.2)',
          }}
        >
          <span className="material-symbols-outlined text-[18px]">analytics</span>
          Run unbaised Analysis
        </button>

        <div className="pt-3 border-t space-y-1" style={{ borderColor: 'rgba(66,71,84,0.2)' }}>
          <a href="#" className="flex items-center gap-3 py-2 px-4 rounded-lg text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 transition-all">
            <span className="material-symbols-outlined text-[16px]">cloud_done</span>
            System Status
          </a>
          <a href="#" className="flex items-center gap-3 py-2 px-4 rounded-lg text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 transition-all">
            <span className="material-symbols-outlined text-[16px]">settings</span>
            Settings
          </a>
        </div>
      </div>
    </aside>
  );
}
