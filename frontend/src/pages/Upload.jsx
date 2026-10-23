import { CheckCircle2, FileSpreadsheet, FileUp, Loader2, XCircle } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, ErrorState, Notice, OutcomeBadge, PageHeader, SignalBadge } from '../components/ui'
import { api, saveBlob } from '../lib/api'
import { useDataset } from '../lib/dataset'
import { formatNumber, formatPct, formatUsd } from '../lib/format'
import { checkUploadFile, MAX_UPLOAD_MB as MAX_MB } from '../lib/validation'

const SAMPLE = [
  'Company Name,Founded Year,Session,Funding,City,Industry,Status',
  'Acme Robotics,2012,Summer,$2.5M,San Francisco,"Hardware, Robotics",Operating',
  'Beta Health,2009,Winter,0,Boston,Health Care,Closed',
  'Gamma Pay,2011,Summer,750k,New York City,"Finance, Payments",Acquired',
  'Delta Learn,2013,Winter,,London,Education,',
].join('\n')

export default function Upload() {
  const { dataset, setDataset } = useDataset()
  const input = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [stage, setStage] = useState('idle')
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [created, setCreated] = useState(null)

  const pick = async (selected) => {
    setReport(null)
    setCreated(null)
    setError(null)
    const problem = checkUploadFile(selected)
    setFile(selected || null)
    if (problem) {
      setError({ message: problem })
      return
    }
    setStage('validating')
    try {
      const response = await api.validateDataset(selected)
      setReport(response.data)
    } catch (err) {
      setError(err)
    } finally {
      setStage('idle')
    }
  }

  const activate = async () => {
    setStage('uploading')
    setError(null)
    try {
      const response = await api.uploadDataset(file)
      setCreated(response.data)
      setDataset(response.data)
    } catch (err) {
      setError(err)
    } finally {
      setStage('idle')
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Data upload"
        title="Analyse your own startup list"
        description="Upload a CSV, review how its columns map to the model, preview the scored rows, then make it the active dataset for the explorer, dashboard and reports."
        actions={
          <button className="btn-secondary" onClick={() => saveBlob(new Blob([SAMPLE], { type: 'text/csv' }), 'sample_startups.csv')}>
            <FileSpreadsheet size={15} aria-hidden /> Download sample CSV
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="1. Choose a CSV file" className="lg:col-span-2">
          <div
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              pick(event.dataTransfer.files?.[0])
            }}
            className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragging ? 'border-brand-600 bg-brand-50' : 'border-slate-300 bg-slate-50/60'
            }`}
          >
            {stage === 'validating' ? <Loader2 className="animate-spin text-brand-700" size={28} aria-hidden /> : <FileUp className="text-slate-400" size={28} aria-hidden />}
            <p className="mt-3 text-sm font-medium text-slate-800">{file ? file.name : 'Drag and drop a CSV file here'}</p>
            <p className="mt-1 text-xs text-slate-500">
              {stage === 'validating' ? 'Validating and scoring…' : `CSV only · up to ${MAX_MB} MB · up to 5,000 rows`}
            </p>
            <button className="btn-secondary mt-4" onClick={() => input.current?.click()} disabled={stage !== 'idle'}>
              Browse files
            </button>
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              data-testid="file-input"
              onChange={(event) => {
                pick(event.target.files?.[0])
                event.target.value = ''
              }}
            />
          </div>
          {error && <ErrorState error={error} className="mt-4" />}
        </Card>
        <Card title="Accepted columns">
          <ul className="space-y-2 text-sm text-slate-600">
            <li><strong className="text-slate-800">Required:</strong> a year column (YCYear, Year, Founded Year, Batch Year…)</li>
            <li><strong className="text-slate-800">Recommended:</strong> Company / Company Name, Funding / TotalFunds, City / Location, Industry / Market1-5, Session</li>
            <li><strong className="text-slate-800">Optional:</strong> Description, Website, Status / Fate, Founders, Investors</li>
          </ul>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            Uploads are held in server memory for about two hours and are never written to disk. Revenue or other columns
            the model was not trained on are ignored.
          </p>
        </Card>
      </div>

      {report && (
        <div className="mt-6 space-y-6 fade-in" data-testid="upload-report">
          <Card title="2. Validation results" subtitle={report.filename}>
            <div className="grid gap-4 sm:grid-cols-3">
              <Metric label="Rows" value={formatNumber(report.rows)} />
              <Metric label="Scorable by the model" value={formatNumber(report.scorable_rows)} />
              <Metric label="Rows with issues" value={formatNumber(report.rows_with_issues)} />
            </div>
            {report.warnings.length > 0 && (
              <div className="mt-4 space-y-2">
                {report.warnings.map((warning) => (
                  <Notice key={warning} tone="warning">
                    {warning}
                  </Notice>
                ))}
              </div>
            )}
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="text-left text-xs text-slate-500">
                  <tr>
                    <th className="py-2 font-medium">Concept</th>
                    <th className="py-2 font-medium">Level</th>
                    <th className="py-2 font-medium">Matched column(s)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {report.columns.map((column) => (
                    <tr key={column.concept}>
                      <td className="py-2 text-slate-800">{column.label}</td>
                      <td className="py-2 text-xs text-slate-500 capitalize">{column.level}</td>
                      <td className="py-2">
                        {column.found ? (
                          <span className="inline-flex items-center gap-1.5 text-slate-700">
                            <CheckCircle2 size={14} className="text-good" aria-hidden /> {column.columns.join(', ')}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-slate-400">
                            <XCircle size={14} aria-hidden /> Not found
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {report.unused_columns.length > 0 && <p className="mt-3 text-xs text-slate-500">Ignored columns: {report.unused_columns.join(', ')}</p>}
            {report.issues.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-semibold text-slate-800">Rows that cannot be scored</p>
                <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-xs text-slate-600">
                  {report.issues.map((issue) => (
                    <li key={issue.row_number}>
                      Row {issue.row_number} ({issue.name}): {Object.entries(issue.issues).map(([k, v]) => `${k} ${v}`).join('; ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <Card title="3. Preview" subtitle={`First ${report.preview.length} rows with model estimates`}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-slate-50 text-left text-xs text-slate-500">
                  <tr>
                    {['Row', 'Name', 'Year', 'City', 'Funding', 'Markets', 'Status', 'Model class', 'P(Dead)', 'Signal'].map((h) => (
                      <th key={h} className="px-3 py-2 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {report.preview.map((row) => (
                    <tr key={row.id}>
                      <td className="num px-3 py-2 text-slate-500">{row.row_number}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">{row.name}</td>
                      <td className="num px-3 py-2">{row.year ?? '—'}</td>
                      <td className="px-3 py-2">{row.city || '—'}</td>
                      <td className="num px-3 py-2">{formatUsd(row.total_funding)}</td>
                      <td className="max-w-40 truncate px-3 py-2">{row.markets.join(', ') || '—'}</td>
                      <td className="px-3 py-2"><OutcomeBadge outcome={row.status} /></td>
                      <td className="px-3 py-2">
                        {row.prediction ? <OutcomeBadge outcome={row.prediction.predicted_outcome} /> : <span className="text-xs text-amber-700">Not scored</span>}
                      </td>
                      <td className="num px-3 py-2">{row.prediction ? formatPct(row.prediction.probabilities.Dead) : '—'}</td>
                      <td className="px-3 py-2"><SignalBadge level={row.prediction?.failure_signal} compact /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="4. Use this dataset">
            {created ? (
              <div className="space-y-3" data-testid="upload-success">
                <p className="flex items-center gap-2 text-sm font-medium text-slate-800">
                  <CheckCircle2 className="text-good" size={18} aria-hidden /> “{created.name}” is now the active dataset ({created.rows} rows,{' '}
                  {created.scored_rows} scored).
                </p>
                <div className="flex flex-wrap gap-2">
                  <Link className="btn-primary" to="/explorer">Open in explorer</Link>
                  <Link className="btn-secondary" to="/">View dashboard</Link>
                  <Link className="btn-secondary" to="/reports">Generate reports</Link>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-600">
                  {report.scorable_rows > 0
                    ? `Load ${report.rows} rows as the active dataset (currently: ${dataset.name}).`
                    : 'No rows can be scored. Fix the issues above and upload again.'}
                </p>
                <button className="btn-primary" onClick={activate} disabled={stage !== 'idle' || report.scorable_rows === 0} data-testid="activate-dataset">
                  {stage === 'uploading' ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
                  Use this dataset
                </button>
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="num mt-0.5 text-xl font-semibold text-navy-900">{value}</p>
    </div>
  )
}
