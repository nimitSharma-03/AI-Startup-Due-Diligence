import { BarChart3, BookOpen, Database, FileText, LayoutDashboard, Menu, Search, Sparkles, Upload, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useDataset } from '../lib/dataset'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/explorer', label: 'Startup Explorer', icon: Search },
  { to: '/predict', label: 'Predict', icon: Sparkles },
  { to: '/upload', label: 'Data Upload', icon: Upload },
  { to: '/analytics', label: 'Model Analytics', icon: BarChart3 },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/about', label: 'Methodology', icon: BookOpen },
]

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5 text-white">
      <span className="grid size-8 place-items-center rounded-lg bg-white/10 ring-1 ring-white/15">
        <svg viewBox="0 0 32 32" className="size-5" aria-hidden>
          <path d="M8 22V10h6.5a6 6 0 0 1 0 12H8z" fill="none" stroke="#5eead4" strokeWidth="2.8" />
          <circle cx="23.5" cy="10" r="2.4" fill="#5eead4" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold tracking-tight">Diligence AI</span>
        <span className="block text-[11px] text-slate-400">Startup due diligence</span>
      </span>
    </NavLink>
  )
}

function NavItems({ onNavigate }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
              isActive ? 'bg-white/10 font-medium text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'
            }`
          }
        >
          <Icon size={17} aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function DatasetPill() {
  const { dataset, resetToReference, isReference } = useDataset()
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs">
      <p className="flex items-center gap-1.5 font-semibold text-slate-200">
        <Database size={13} aria-hidden /> Active dataset
      </p>
      <p className="mt-1 line-clamp-2 text-slate-400" title={dataset.name}>
        {dataset.name}
      </p>
      {!isReference && (
        <button onClick={resetToReference} className="mt-2 text-brand-500 underline-offset-2 hover:underline">
          Use reference dataset
        </button>
      )}
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <div className="min-h-screen lg:pl-64">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col justify-between bg-navy-900 px-4 py-5 lg:flex">
        <div className="flex flex-col gap-7">
          <Brand />
          <NavItems />
        </div>
        <DatasetPill />
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-navy-900 px-4 py-3 lg:hidden">
        <Brand />
        <button className="rounded-lg p-2 text-slate-200 hover:bg-white/10" onClick={() => setOpen(true)} aria-label="Open navigation" aria-expanded={open}>
          <Menu size={20} />
        </button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button className="absolute inset-0 bg-navy-950/60" onClick={() => setOpen(false)} aria-label="Close navigation" />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col justify-between bg-navy-900 px-4 py-5">
            <div className="flex flex-col gap-7">
              <div className="flex items-center justify-between">
                <Brand />
                <button className="rounded-lg p-2 text-slate-200 hover:bg-white/10" onClick={() => setOpen(false)} aria-label="Close navigation">
                  <X size={20} />
                </button>
              </div>
              <NavItems onNavigate={() => setOpen(false)} />
            </div>
            <DatasetPill />
          </div>
        </div>
      )}

      <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Outlet />
        <footer className="mt-12 border-t border-slate-200 pt-5 text-xs leading-5 text-slate-500">
          For educational and analytical use only. Model outputs are statistical associations from historical data, not
          investment, legal or financial advice.
        </footer>
      </main>
    </div>
  )
}
