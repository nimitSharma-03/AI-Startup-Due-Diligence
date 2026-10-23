import { AlertTriangle, CheckCircle2, CircleAlert, Info, Loader2, OctagonAlert, RefreshCw } from 'lucide-react'
import { useDataset } from '../lib/dataset'
import { OUTCOME_COLORS, OUTCOME_HELP } from '../lib/format'

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-navy-900 sm:text-[1.7rem]">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

export function Card({ title, subtitle, actions, children, className = '', bodyClassName = '' }) {
  return (
    <section className={`card fade-in ${className}`}>
      {(title || actions) && (
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-navy-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs leading-5 text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className={`card-pad ${bodyClassName}`}>{children}</div>
    </section>
  )
}

export function StatTile({ label, value, hint, icon: Icon }) {
  return (
    <div className="card fade-in p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
        {Icon && <Icon size={16} className="text-slate-400" aria-hidden />}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-navy-900">{value}</p>
      {hint && <p className="mt-1 text-xs leading-5 text-slate-500">{hint}</p>}
    </div>
  )
}

export function OutcomeBadge({ outcome, label }) {
  if (!outcome) return <span className="text-xs text-slate-400">—</span>
  return (
    <span
      title={OUTCOME_HELP[outcome] || outcome}
      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-700"
    >
      <span className="size-2 rounded-full" style={{ background: OUTCOME_COLORS[outcome] || '#94a3b8' }} aria-hidden />
      {label || outcome}
    </span>
  )
}

const SIGNALS = {
  Lower: { icon: CheckCircle2, className: 'text-good', bg: 'bg-green-50 border-green-200' },
  Moderate: { icon: CircleAlert, className: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' },
  Elevated: { icon: OctagonAlert, className: 'text-critical', bg: 'bg-red-50 border-red-200' },
}

export function SignalBadge({ level, compact = false }) {
  if (!level) return <span className="text-xs text-slate-400">—</span>
  const spec = SIGNALS[level]
  const Icon = spec.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium text-slate-800 ${spec.bg}`}>
      <Icon size={13} className={spec.className} aria-hidden />
      {level}
      {!compact && <span className="sr-only"> failure-pattern signal</span>}
    </span>
  )
}

export function SourceTag({ source }) {
  const model = source === 'model'
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${
        model ? 'bg-navy-900/5 text-navy-800' : 'bg-brand-50 text-brand-800'
      }`}
    >
      {model ? 'Model' : 'Dataset'}
    </span>
  )
}

export function Loading({ label = 'Loading…', className = '' }) {
  return (
    <div role="status" className={`flex min-h-40 items-center justify-center gap-2 text-sm text-slate-500 ${className}`}>
      <Loader2 className="animate-spin" size={18} aria-hidden />
      {label}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/70 ${className}`} />
}

export function ErrorState({ error, onRetry, className = '' }) {
  const { resetToReference } = useDataset()
  const expired = error?.code === 'dataset_not_found'
  return (
    <div role="alert" className={`card flex flex-col items-start gap-3 border-red-200 bg-red-50/40 p-5 ${className}`}>
      <div className="flex items-start gap-2 text-sm text-red-800">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden />
        <div>
          <p className="font-semibold">{expired ? 'Uploaded dataset unavailable' : 'Something went wrong'}</p>
          <p className="mt-0.5 text-red-700">{error?.message || 'Unexpected error.'}</p>
        </div>
      </div>
      <div className="flex gap-2">
        {expired && (
          <button className="btn-primary" onClick={resetToReference}>
            Switch to reference dataset
          </button>
        )}
        {onRetry && !expired && (
          <button className="btn-secondary" onClick={onRetry}>
            <RefreshCw size={14} aria-hidden /> Retry
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {children && <div className="max-w-md text-sm text-slate-500">{children}</div>}
      {action}
    </div>
  )
}

export function Notice({ tone = 'info', title, children }) {
  const tones = {
    info: { icon: Info, cls: 'border-sky-200 bg-sky-50 text-sky-900' },
    warning: { icon: AlertTriangle, cls: 'border-amber-200 bg-amber-50 text-amber-900' },
  }
  const { icon: Icon, cls } = tones[tone]
  return (
    <div className={`flex gap-2.5 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden />
      <div className="leading-6">
        {title && <p className="font-semibold">{title}</p>}
        {children}
      </div>
    </div>
  )
}

export function KeyValue({ items }) {
  return (
    <dl className="divide-y divide-slate-100">
      {items.map(([label, value]) => (
        <div key={label} className="grid grid-cols-1 gap-1 py-2.5 sm:grid-cols-3 sm:gap-4">
          <dt className="text-xs font-semibold tracking-wide text-slate-500 uppercase sm:pt-0.5">{label}</dt>
          <dd className="text-sm break-words text-slate-800 sm:col-span-2">
            {value === null || value === undefined || value === '' || (Array.isArray(value) && !value.length) ? (
              <span className="text-slate-400">Not provided</span>
            ) : (
              value
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}
