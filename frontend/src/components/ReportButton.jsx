import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { api, saveBlob } from '../lib/api'

/** Fetch the company-specific PDF and save it, with loading and error states. */
export default function ReportButton({ datasetId, startupId, label = 'Download PDF report', className = 'btn-primary', onError }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const download = async () => {
    setBusy(true)
    setError(null)
    try {
      const { blob, filename } = await api.downloadReport(datasetId, startupId)
      saveBlob(blob, filename)
    } catch (err) {
      setError(err.message)
      onError?.(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button className={className} onClick={download} disabled={busy} data-testid="download-report">
        {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : <Download size={15} aria-hidden />}
        {busy ? 'Generating report…' : label}
      </button>
      {error && (
        <p role="alert" className="text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
