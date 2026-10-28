import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

const NAV = [
  { to:'/dashboard',    icon:'ti-layout-dashboard', label:'Dashboard' },
  { to:'/import',       icon:'ti-upload',           label:'Import' },
  { to:'/transactions', icon:'ti-list',             label:'Transactions' },
  { to:'/reports',      icon:'ti-chart-bar',        label:'Reports' },
  { to:'/ml',           icon:'ti-robot',            label:'Insights', badge:'ML' },
  { to:'/portfolio',    icon:'ti-trending-up',      label:'Portfolio', badge:'LIVE' },
  { to:'/networth',     icon:'ti-scale',            label:'Net Worth' },
  { to:'/loans',        icon:'ti-receipt',          label:'Loans' },
];

/** The top panel: brand on the left, page links in the middle (scrolls sideways on
 *  narrow screens rather than wrapping), account on the right. */
export default function TopBar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <header className="flex h-14 flex-shrink-0 items-stretch gap-4 border-b border-line bg-spine px-4 text-ink">
      <div className="flex flex-shrink-0 items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-sm bg-gradient-to-br from-slateblue to-periwinkle">
          <i className="ti ti-chart-pie text-base text-richblack"/>
        </span>
        <span className="hidden font-mono text-sm font-medium tracking-tight text-accent-soft sm:inline">FinTrack Pro</span>
      </div>

      <nav aria-label="Main" className="nav-strip flex min-w-0 flex-1 items-stretch gap-0.5 overflow-x-auto">
        {NAV.map(({ to, icon, label, badge }) => (
          <NavLink key={to} to={to} title={label}
            className={({ isActive }) => `t-item ${isActive ? 'active' : ''}`}>
            <i className={`ti ${icon} text-base`}/>
            <span>{label}</span>
            {badge && <span className="rounded-sm border border-accent-text/50 px-1 py-px font-mono text-[9px] leading-none text-accent-text">{badge}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="flex flex-shrink-0 items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-brand-600 text-xs font-semibold text-white"
          title={user?.email || ''}>
          {(user?.full_name || 'U')[0].toUpperCase()}
        </div>
        <p className="hidden max-w-[9rem] truncate text-sm text-ink xl:block">{user?.full_name || 'User'}</p>
        <button onClick={() => { logout(); nav('/login'); }} title="Sign out" aria-label="Sign out"
          className="rounded-sm px-2 py-1.5 text-xs text-slate-400 hover:bg-white/5 hover:text-ink">
          <i className="ti ti-logout"/><span className="ml-1.5 hidden md:inline">Sign out</span>
        </button>
      </div>
    </header>
  );
}
