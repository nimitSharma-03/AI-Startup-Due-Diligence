import { AlertTriangle, CheckCircle2, ClipboardList, Info } from 'lucide-react'
import { useState } from 'react'
import { ContributionBars, ProbabilityBars } from './charts'
import { Card, Notice, OutcomeBadge, SignalBadge, SourceTag } from './ui'
import { formatPct, formatRatio, OUTCOMES, priorsFrom } from '../lib/format'

export function PredictionCard({ prediction, outOfFold, split }) {
  const priors = priorsFrom(prediction)
  return (
    <Card title="Model prediction" subtitle="Calibrated Random Forest · estimated outcome-class probabilities" actions={<SourceTag source="model" />}>
      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-slate-500">Model-assigned class</p>
          <div className="mt-1">
            <OutcomeBadge outcome={prediction.predicted_outcome} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatRatio(prediction.lift_vs_base_rate[prediction.predicted_outcome])} its base rate</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Most likely class</p>
          <div className="mt-1">
            <OutcomeBadge outcome={prediction.most_likely_outcome} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatPct(prediction.probabilities[prediction.most_likely_outcome])} probability</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Failure-pattern signal</p>
          <div className="mt-1">
            <SignalBadge level={prediction.failure_signal.level} />
          </div>
          <p className="mt-1 text-xs text-slate-500">P(Dead) at {formatRatio(prediction.failure_signal.ratio_to_base_rate)} base rate</p>
        </div>
      </div>
      <ProbabilityBars probabilities={prediction.probabilities} priors={priors} />
      <details className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-600">
        <summary className="cursor-pointer font-semibold text-slate-700">How to read this</summary>
        <p className="mt-2">
          The probabilities estimate how often companies with these attributes ended up in each recorded status in the
          historical data. Because {formatPct(priors.Operating, 0)} of training companies are Operating, the most likely class is usually Operating. The
          model-assigned class instead picks the outcome whose probability most exceeds its base rate (a balanced decision
          rule), which is better at surfacing exit- and failure-like profiles. Neither is a calibrated measure of investment
          risk.
        </p>
      </details>
      {outOfFold && (
        <div className="mt-4 rounded-lg border border-slate-200 px-4 py-3 text-xs leading-5 text-slate-600">
          <p className="font-semibold text-slate-700">Cross-validated estimate (model fitted without this company)</p>
          <p className="num mt-1">{OUTCOMES.map((label) => `${label} ${formatPct(outOfFold[label])}`).join(' · ')}</p>
          <p className="mt-1">
            This company was in the deployed model&apos;s <strong>{split}</strong> split
            {split === 'train' ? ', so the main estimate above is in-sample and likely optimistic.' : ' and was never seen during fitting.'}
          </p>
        </div>
      )}
    </Card>
  )
}

export function ContributionCard({ explanation, defaultOutcome }) {
  const [outcome, setOutcome] = useState(defaultOutcome || 'Dead')
  return (
    <Card
      title="Influencing inputs"
      subtitle="How each input moves the estimate compared with typical training companies"
      actions={<SourceTag source="model" />}
    >
      <div className="mb-4 inline-flex rounded-lg border border-slate-200 p-0.5" role="group" aria-label="Outcome to explain">
        {OUTCOMES.map((label) => (
          <button
            key={label}
            onClick={() => setOutcome(label)}
            aria-pressed={outcome === label}
            className={`rounded-md px-3 py-1 text-xs font-medium ${outcome === label ? 'bg-navy-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            P({label})
          </button>
        ))}
      </div>
      <ContributionBars explanation={explanation} outcome={outcome} />
      <p className="mt-4 text-xs leading-5 text-slate-500">
        Each input is swapped for values from 50 typical training companies while the others stay fixed; the bar is the
        change in estimated probability (percentage points). This describes the model&apos;s behaviour, not causation.
      </p>
    </Card>
  )
}

function IndicatorList({ items, kind }) {
  const Icon = kind === 'risk' ? AlertTriangle : CheckCircle2
  if (!items.length) return <p className="text-sm text-slate-500">None triggered by the available data.</p>
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.title} className="flex gap-3">
          <Icon size={16} className={`mt-0.5 shrink-0 ${kind === 'risk' ? 'text-critical' : 'text-good'}`} aria-hidden />
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-800">
              {item.title} <SourceTag source={item.source} />
            </p>
            <p className="mt-0.5 text-sm leading-6 text-slate-600">{item.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function IndicatorsGrid({ insights }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Risk indicators" subtitle={`${insights.risks.length} triggered`}>
        <IndicatorList items={insights.risks} kind="risk" />
      </Card>
      <Card title="Strength indicators" subtitle={`${insights.strengths.length} triggered`}>
        <IndicatorList items={insights.strengths} kind="strength" />
      </Card>
    </div>
  )
}

export function LimitationsCard({ insights, missingFields = [], warnings = [] }) {
  const labels = { year: 'Batch year', session: 'Batch session', total_funding: 'Total funding', city: 'City', markets: 'Markets' }
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Confidence, limitations and data gaps">
        {missingFields.length > 0 && (
          <div className="mb-4">
            <Notice tone="warning" title="Model inputs not provided">
              {missingFields.map((field) => labels[field] || field).join(', ')}. Missing inputs are imputed by the model and flagged.
            </Notice>
          </div>
        )}
        {warnings.length > 0 && (
          <div className="mb-4">
            <Notice tone="warning">{warnings.join(' ')}</Notice>
          </div>
        )}
        <ul className="space-y-2.5 text-sm leading-6 text-slate-600">
          {insights.limitations.map((item) => (
            <li key={item} className="flex gap-2.5">
              <Info size={15} className="mt-1 shrink-0 text-slate-400" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Diligence considerations" subtitle="Questions that follow from what is present or missing. Not a recommendation.">
        <ul className="space-y-2.5 text-sm leading-6 text-slate-600">
          {insights.considerations.map((item) => (
            <li key={item} className="flex gap-2.5">
              <ClipboardList size={15} className="mt-1 shrink-0 text-brand-700" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

export function SummaryCard({ paragraphs }) {
  return (
    <Card title="Executive summary" subtitle="Generated deterministically from the structured data below. No language model is used.">
      <div className="space-y-3 text-sm leading-6 text-slate-700">
        {paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </Card>
  )
}
