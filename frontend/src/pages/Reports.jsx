import { Eye, FileText, Loader2, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ReportButton from '../components/ReportButton'
import { Card, EmptyState, ErrorState, Loading, OutcomeBadge, PageHeader, SignalBadge } from '../components/ui'
import { api } from '../lib/api'
import { useDataset } from '../lib/dataset'
import { formatUsd } from '../lib/format'
import { useApi } from '../lib/useApi'

const SECTIONS = [
  'Cover page and report date',
  'Executive summary',
  'Company profile (dataset facts)',
  'Available financial information',
  'Funding analysis vs. reference set',
  'Model prediction and probabilities',
  'Model confidence and limitations',
  'Risk and strength indicators',
  'Feature contribution analysis',
  'Investment-related considerations',
  'Data quality disclosures',
  'Methodology and disclaimer',
]

export default function Reports() {
  const { dataset } = useDataset()
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [selection, setSelection] = useState(null)
  // A selection belongs to one dataset; switching datasets clears it.
  const selected = selection?.datasetId === dataset.id ? selection.row : null
  const [preview, setPreview] = useState({ url: null, loading: false, error: null })

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query), 250)
    return () => clearTimeout(id)
  }, [query])
  useEffect(() => {
    return () => preview.url && URL.revokeObjectURL(preview.url)
  }, [preview.url])

  const results = useApi(() => api.startups(dataset.id, { q: debounced, page_size: 12, sort: 'name' }), [dataset.id, debounced])

  const choose = (row) => {
    setSelection({ datasetId: dataset.id, row })
    setPreview({ url: null, loading: false, error: null })
  }

  const loadPreview = async () => {
    setPreview({ url: null, loading: true, error: null })
    try {
      const { blob } = await api.downloadReport(dataset.id, selected.id)
      setPreview({ url: URL.createObjectURL(blob), loading: false, error: null })
    } catch (error) {
      setPreview({ url: null, loading: false, error })
    }
  }

  const rows = results.data?.data || []
  return (
    <>
      <PageHeader
        eyebrow="Reports"
        title="Company due diligence reports"
        description={`Select any startup in ${dataset.name} to generate its own PDF report. Reports are built on demand from that company's record only.`}
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <Card title="1. Select a startup" bodyClassName="!p-0">
          <div className="border-b border-slate-100 p-4">
            <label className="relative block">
              <span className="sr-only">Search startups</span>
              <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400" aria-hidden />
              <input className="input pl-9" placeholder="Search by name or market…" value={query} onChange={(e) => setQuery(e.target.value)} data-testid="report-search" />
            </label>
          </div>
          {results.error && <ErrorState error={results.error} onRetry={results.reload} className="m-4" />}
          {results.loading && !rows.length && <Loading label="Searching…" />}
          {!results.loading && !results.error && rows.length === 0 && <EmptyState title="No matching startups" />}
          <ul className="max-h-[480px] divide-y divide-slate-100 overflow-auto" role="listbox" aria-label="Startups">
            {rows.map((row) => (
              <li key={row.id}>
                <button
                  role="option"
                  aria-selected={selected?.id === row.id}
                  onClick={() => choose(row)}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50 ${selected?.id === row.id ? 'bg-brand-50' : ''}`}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-800">{row.name}</span>
                    <span className="block truncate text-xs text-slate-500">
                      {[row.year, row.city, row.markets[0]].filter(Boolean).join(' · ') || 'No details'}
                    </span>
                  </span>
                  <OutcomeBadge outcome={row.prediction?.predicted_outcome} />
                </button>
              </li>
            ))}
          </ul>
          {results.data?.meta && (
            <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
              Showing {rows.length} of {results.data.meta.total}. Refine the search to find others.
            </p>
          )}
        </Card>

        <div className="min-w-0 space-y-6">
          {!selected ? (
            <Card>
              <EmptyState title="No startup selected">
                Choose a company on the left. Each report includes:
                <ul className="mt-3 grid gap-1 text-left text-xs text-slate-600 sm:grid-cols-2">
                  {SECTIONS.map((section) => (
                    <li key={section}>• {section}</li>
                  ))}
                </ul>
              </EmptyState>
            </Card>
          ) : (
            <Card title="2. Generate the report" subtitle={`Selected: ${selected.name}`}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-2 text-sm">
                  <p className="flex items-center gap-2 text-lg font-semibold text-navy-900" data-testid="selected-startup">
                    <FileText size={18} className="text-brand-700" aria-hidden /> {selected.name}
                  </p>
                  <p className="text-slate-600">
                    {[selected.year && `Batch ${selected.session ? `${selected.session} ` : ''}${selected.year}`, selected.city, formatUsd(selected.total_funding) !== '—' && `Funding ${formatUsd(selected.total_funding)}`]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-500">Recorded</span> <OutcomeBadge outcome={selected.status} />
                    <span className="ml-2 text-xs text-slate-500">Model</span> <OutcomeBadge outcome={selected.prediction?.predicted_outcome} />
                    <SignalBadge level={selected.prediction?.failure_signal} compact />
                  </div>
                  <Link to={`/startups/${selected.id}`} className="inline-block text-xs text-brand-700 hover:underline">
                    View full analysis
                  </Link>
                </div>
                <div className="flex flex-wrap gap-2">
                  <ReportButton datasetId={dataset.id} startupId={selected.id} />
                  <button className="btn-secondary" onClick={loadPreview} disabled={preview.loading}>
                    {preview.loading ? <Loader2 size={15} className="animate-spin" aria-hidden /> : <Eye size={15} aria-hidden />} Preview
                  </button>
                </div>
              </div>
              {preview.error && <ErrorState error={preview.error} className="mt-4" />}
              {preview.url && (
                <iframe title={`Report preview for ${selected.name}`} src={preview.url} className="mt-5 h-[720px] w-full rounded-lg border border-slate-200" />
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  )
}
