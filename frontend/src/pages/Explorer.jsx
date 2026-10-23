import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, Filter, Search, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Card, EmptyState, ErrorState, Loading, OutcomeBadge, PageHeader, SignalBadge } from '../components/ui'
import { api, exportUrl } from '../lib/api'
import { useDataset } from '../lib/dataset'
import { formatNumber, formatPct, formatUsd } from '../lib/format'
import { useApi } from '../lib/useApi'

const FILTER_KEYS = ['q', 'industry', 'city', 'status', 'predicted', 'signal', 'year_min', 'year_max', 'funding_min']
const COLUMNS = [
  { key: 'name', label: 'Startup', sortable: true },
  { key: 'year', label: 'Batch', sortable: true },
  { key: 'city', label: 'City', sortable: true },
  { key: 'markets', label: 'Industry' },
  { key: 'total_funding', label: 'Funding', sortable: true, align: 'right' },
  { key: 'status', label: 'Recorded status', sortable: true },
  { key: 'predicted', label: 'Model class' },
  { key: 'p_dead', label: 'P(Dead)', sortable: true, align: 'right' },
  { key: 'signal', label: 'Signal' },
]

function useDebounced(value, delay = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

export default function Explorer() {
  const { dataset } = useDataset()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') || '')
  const [showFilters, setShowFilters] = useState(false)
  const debounced = useDebounced(search)

  const query = useMemo(() => {
    const result = { sort: params.get('sort') || 'name', order: params.get('order') || 'asc', page: params.get('page') || '1', page_size: '25' }
    for (const key of FILTER_KEYS) if (params.get(key)) result[key] = params.get(key)
    return result
  }, [params])

  useEffect(() => {
    if ((params.get('q') || '') === debounced) return
    const next = new URLSearchParams(params)
    if (debounced) next.set('q', debounced)
    else next.delete('q')
    next.delete('page')
    setParams(next, { replace: true })
  }, [debounced, params, setParams])

  const facets = useApi(() => api.facets(dataset.id), [dataset.id])
  const list = useApi(() => api.startups(dataset.id, query), [dataset.id, JSON.stringify(query)])

  const update = (key, value) => {
    const next = new URLSearchParams(params)
    if (value === '' || value == null) next.delete(key)
    else next.set(key, value)
    if (key !== 'page') next.delete('page')
    setParams(next)
  }
  const toggleSort = (key) => {
    const next = new URLSearchParams(params)
    const same = (params.get('sort') || 'name') === key
    next.set('sort', key)
    next.set('order', same && (params.get('order') || 'asc') === 'asc' ? 'desc' : key === 'name' ? 'asc' : 'desc')
    next.delete('page')
    setParams(next)
  }
  const clear = () => {
    setSearch('')
    setParams(new URLSearchParams())
  }

  const activeFilters = FILTER_KEYS.filter((key) => key !== 'q' && params.get(key))
  const rows = list.data?.data || []
  const meta = list.data?.meta
  const f = facets.data?.data

  return (
    <>
      <PageHeader
        eyebrow="Startup Explorer"
        title="Search and screen startups"
        description="Every row shows dataset attributes alongside the model's estimate. Select a company to see its full analysis and download its report."
        actions={
          <a className="btn-secondary" href={exportUrl(dataset.id, query)} download>
            <Download size={15} aria-hidden /> Export CSV
          </a>
        }
      />

      <Card bodyClassName="!p-0">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center">
          <label className="relative flex-1">
            <span className="sr-only">Search startups</span>
            <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              className="input pl-9"
              placeholder="Search by name, description or market…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              data-testid="explorer-search"
            />
          </label>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => setShowFilters((v) => !v)} aria-expanded={showFilters} aria-controls="explorer-filters">
              <Filter size={15} aria-hidden /> Filters{activeFilters.length ? ` (${activeFilters.length})` : ''}
            </button>
            {(activeFilters.length > 0 || search) && (
              <button className="btn-ghost" onClick={clear}>
                <X size={15} aria-hidden /> Clear
              </button>
            )}
          </div>
        </div>

        {showFilters && (
          <div id="explorer-filters" className="grid gap-3 border-b border-slate-100 bg-slate-50/60 p-4 sm:grid-cols-2 lg:grid-cols-4">
            <Select label="Industry" value={params.get('industry')} onChange={(v) => update('industry', v)} options={f?.industries?.map((i) => [i.name, `${i.name} (${i.count})`])} />
            <Select label="City" value={params.get('city')} onChange={(v) => update('city', v)} options={f?.cities?.map((i) => [i.name, `${i.name} (${i.count})`])} />
            <Select label="Recorded status" value={params.get('status')} onChange={(v) => update('status', v)} options={f?.statuses?.map((s) => [s, s])} />
            <Select label="Model class" value={params.get('predicted')} onChange={(v) => update('predicted', v)} options={f?.predicted?.map((s) => [s, s])} />
            <Select label="Failure signal" value={params.get('signal')} onChange={(v) => update('signal', v)} options={f?.signals?.map((s) => [s, s])} />
            <Select label="Batch year from" value={params.get('year_min')} onChange={(v) => update('year_min', v)} options={f?.years?.map((y) => [String(y), String(y)])} />
            <Select label="Batch year to" value={params.get('year_max')} onChange={(v) => update('year_max', v)} options={f?.years?.map((y) => [String(y), String(y)])} />
            <Select
              label="Minimum funding"
              value={params.get('funding_min')}
              onChange={(v) => update('funding_min', v)}
              options={[['1', 'Any reported > $0'], ['100000', '$100K+'], ['1000000', '$1M+'], ['10000000', '$10M+']]}
            />
          </div>
        )}

        {list.error && <ErrorState error={list.error} onRetry={list.reload} className="m-4" />}
        {!list.error && (
          <div className="relative">
            {list.loading && rows.length > 0 && <div className="absolute inset-0 z-10 bg-white/50" aria-hidden />}
            {list.loading && !rows.length ? (
              <Loading label="Loading startups…" />
            ) : rows.length === 0 ? (
              <EmptyState title="No startups match these filters" action={<button className="btn-secondary mt-2" onClick={clear}>Clear filters</button>} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px] text-sm" data-testid="startup-table">
                  <thead className="bg-slate-50 text-left text-xs text-slate-500">
                    <tr>
                      {COLUMNS.map((column) => {
                        const active = query.sort === column.key
                        return (
                          <th key={column.key} scope="col" className={`px-4 py-2.5 font-medium ${column.align === 'right' ? 'text-right' : ''}`} aria-sort={active ? (query.order === 'asc' ? 'ascending' : 'descending') : undefined}>
                            {column.sortable ? (
                              <button className="inline-flex items-center gap-1 hover:text-slate-800" onClick={() => toggleSort(column.key)}>
                                {column.label}
                                {active && (query.order === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                              </button>
                            ) : (
                              column.label
                            )}
                          </th>
                        )
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rows.map((row) => (
                      <tr
                        key={row.id}
                        className="cursor-pointer hover:bg-slate-50"
                        onClick={() => navigate(`/startups/${row.id}`)}
                      >
                        <td className="max-w-56 px-4 py-3">
                          <Link to={`/startups/${row.id}`} className="font-medium text-navy-900 hover:text-brand-700 hover:underline" onClick={(e) => e.stopPropagation()}>
                            {row.name}
                          </Link>
                          {!row.scorable && <p className="text-xs text-amber-700">Not scored: {Object.keys(row.issues).join(', ')}</p>}
                        </td>
                        <td className="num px-4 py-3 whitespace-nowrap text-slate-600">
                          {row.year ?? '—'} {row.session ? <span className="text-slate-400">{row.session[0]}</span> : null}
                        </td>
                        <td className="px-4 py-3 text-slate-600">{row.city || <span className="text-slate-400">—</span>}</td>
                        <td className="max-w-52 truncate px-4 py-3 text-slate-600" title={row.markets.join(', ')}>
                          {row.markets.slice(0, 2).join(', ') || <span className="text-slate-400">—</span>}
                        </td>
                        <td className="num px-4 py-3 text-right text-slate-700">{formatUsd(row.total_funding)}</td>
                        <td className="px-4 py-3">
                          <OutcomeBadge outcome={row.status} />
                        </td>
                        <td className="px-4 py-3">
                          <OutcomeBadge outcome={row.prediction?.predicted_outcome} />
                        </td>
                        <td className="num px-4 py-3 text-right font-medium">{row.prediction ? formatPct(row.prediction.probabilities.Dead) : '—'}</td>
                        <td className="px-4 py-3">
                          <SignalBadge level={row.prediction?.failure_signal} compact />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {meta && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600 sm:flex-row">
            <p data-testid="result-count">
              {formatNumber(meta.total)} startups · page {meta.page} of {meta.pages}
            </p>
            <div className="flex gap-2">
              <button className="btn-secondary px-3" disabled={meta.page <= 1} onClick={() => update('page', String(meta.page - 1))} aria-label="Previous page">
                <ChevronLeft size={16} />
              </button>
              <button className="btn-secondary px-3" disabled={meta.page >= meta.pages} onClick={() => update('page', String(meta.page + 1))} aria-label="Next page">
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </Card>
    </>
  )
}

function Select({ label, value, onChange, options }) {
  const id = `filter-${label.toLowerCase().replace(/\W+/g, '-')}`
  return (
    <div>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <select id={id} className="input" value={value || ''} onChange={(event) => onChange(event.target.value)}>
        <option value="">Any</option>
        {(options || []).map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  )
}
