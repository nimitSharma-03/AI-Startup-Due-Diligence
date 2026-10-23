import { ArrowLeft, ExternalLink } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ContributionCard, IndicatorsGrid, LimitationsCard, PredictionCard, SummaryCard } from '../components/Analysis'
import ReportButton from '../components/ReportButton'
import { Card, ErrorState, KeyValue, Loading, Notice, OutcomeBadge, PageHeader, SourceTag } from '../components/ui'
import { api } from '../lib/api'
import { useDataset } from '../lib/dataset'
import { formatUsd } from '../lib/format'
import { useApi } from '../lib/useApi'

function safeUrl(value) {
  if (!value) return null
  const url = /^https?:\/\//i.test(value) ? value : `http://${value}`
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null
  } catch {
    return null
  }
}

export default function StartupDetail() {
  const { id } = useParams()
  const { dataset } = useDataset()
  const { data, error, loading, reload } = useApi(() => api.startup(dataset.id, id), [dataset.id, id])
  const startup = data?.data

  return (
    <>
      <Link to="/explorer" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-navy-900">
        <ArrowLeft size={15} aria-hidden /> Back to explorer
      </Link>
      {loading && !startup && <Loading label="Analysing startup…" />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {startup && <Detail startup={startup} datasetId={dataset.id} />}
    </>
  )
}

function Detail({ startup, datasetId }) {
  const website = safeUrl(startup.website)
  const funding = startup.insights.funding_context
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${startup.dataset.kind === 'reference' ? 'Reference dataset' : 'Uploaded dataset'} · row ${startup.row_number}`}
        title={startup.name}
        description={startup.description || undefined}
        actions={<ReportButton datasetId={datasetId} startupId={startup.id} />}
      />
      {!startup.prediction && (
        <Notice tone="warning" title="This record could not be scored">
          {Object.entries(startup.issues)
            .map(([field, message]) => `${field} ${message}`)
            .join('; ')}
        </Notice>
      )}

      <SummaryCard paragraphs={startup.summary} />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Company overview" actions={<SourceTag source="dataset" />}>
            <KeyValue
              items={[
                ['Batch', startup.year ? `${startup.session ? `${startup.session} ` : ''}${startup.year}` : null],
                ['City', startup.city],
                ['Markets', startup.markets.join(', ')],
                ['Founders', startup.founders.join(', ')],
                ['Investors', startup.investors.join(', ')],
                [
                  'Website',
                  website && (
                    <a href={website} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 text-brand-700 hover:underline">
                      {startup.website} <ExternalLink size={12} aria-hidden />
                    </a>
                  ),
                ],
                ['Recorded status', startup.status && <OutcomeBadge outcome={startup.status} />],
              ]}
            />
          </Card>
          <Card title="Available financial information" actions={<SourceTag source="dataset" />}>
            <KeyValue
              items={[
                ['Total funding', funding ? formatUsd(funding.amount, { compact: false }) : null],
                ['Percentile', funding ? `${funding.percentile}th of ${funding.reference_count} reference companies` : null],
                ['Reference median', funding?.reference_median_formatted],
              ]}
            />
            <p className="mt-3 text-xs leading-5 text-slate-500">
              Revenue, burn, runway, valuation and headcount are not in the dataset and are never estimated.
            </p>
          </Card>
        </div>
        <div className="space-y-6 lg:col-span-3">
          {startup.prediction && (
            <PredictionCard prediction={startup.prediction} outOfFold={startup.out_of_fold_probabilities} split={startup.evaluation_split} />
          )}
          {startup.explanation && <ContributionCard explanation={startup.explanation} defaultOutcome={startup.prediction?.predicted_outcome} />}
        </div>
      </div>

      <IndicatorsGrid insights={startup.insights} />
      <LimitationsCard insights={startup.insights} missingFields={startup.missing_fields} warnings={startup.warnings} />

      <Card>
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold text-navy-900">Due diligence report for {startup.name}</p>
            <p className="text-sm text-slate-500">A multi-page PDF with every section above, charts, methodology and disclosures.</p>
          </div>
          <ReportButton datasetId={datasetId} startupId={startup.id} />
        </div>
      </Card>
    </div>
  )
}
