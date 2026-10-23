import { ArrowRight, Building2, CircleDollarSign, Gauge, Target } from 'lucide-react'
import { Link } from 'react-router-dom'
import { DistributionBars, OutcomeBars, YearStatusChart } from '../components/charts'
import { Card, ErrorState, PageHeader, Skeleton, SignalBadge, SourceTag, StatTile } from '../components/ui'
import { api } from '../lib/api'
import { useDataset } from '../lib/dataset'
import { formatNumber, formatPct, formatUsd } from '../lib/format'
import { useApi } from '../lib/useApi'

function OverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  )
}

export default function Overview() {
  const { dataset } = useDataset()
  const { data, error, loading, reload } = useApi(() => api.analytics(dataset.id), [dataset.id])
  const analytics = data?.data

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="Portfolio intelligence dashboard"
        description={`Real figures calculated from ${dataset.name} and the deployed model. Dataset facts and model estimates are labelled separately.`}
        actions={
          <Link to="/explorer" className="btn-primary">
            Explore startups <ArrowRight size={15} aria-hidden />
          </Link>
        }
      />
      {loading && !analytics && <OverviewSkeleton />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {analytics && <OverviewBody analytics={analytics} />}
    </>
  )
}

function OverviewBody({ analytics }) {
  const { totals, funding, model } = analytics
  const holdout = model.holdout
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile icon={Building2} label="Startups in dataset" value={formatNumber(totals.startups)} hint={`${formatNumber(totals.scored)} scored by the model · ${totals.markets} market tags`} />
        <StatTile
          icon={CircleDollarSign}
          label="Median reported funding"
          value={formatUsd(funding.median)}
          hint={`${formatNumber(funding.reported)} report funding · ${formatNumber(funding.zero)} report $0 · ${formatNumber(funding.missing)} missing`}
        />
        <StatTile icon={Target} label="Hold-out balanced accuracy" value={formatPct(holdout.balanced_accuracy)} hint={`Majority-class baseline: 33.3% (3 classes) · macro F1 ${holdout.f1_macro.toFixed(2)}`} />
        <StatTile icon={Gauge} label="Hold-out ROC-AUC (macro)" value={holdout.roc_auc_ovr_macro.toFixed(3)} hint={`Cross-validated ${model.cross_validation.roc_auc_ovr_macro.mean.toFixed(3)} ± ${model.cross_validation.roc_auc_ovr_macro.std.toFixed(3)}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Model-assigned outcome class" subtitle="Balanced decision rule over calibrated probabilities" actions={<SourceTag source="model" />}>
          <OutcomeBars data={analytics.predicted_distribution} />
          <div className="mt-4 grid grid-cols-3 gap-3 border-t border-slate-100 pt-4 text-center">
            {analytics.failure_signal_distribution.map((item) => (
              <div key={item.name}>
                <SignalBadge level={item.name} compact />
                <p className="num mt-1 text-lg font-semibold text-navy-900">{item.count}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">Failure-pattern signal = estimated P(Dead) relative to the {formatPct(model.class_priors.Dead)} training base rate.</p>
        </Card>
        <Card title="Recorded status" subtitle="Status at data collection, from the dataset" actions={<SourceTag source="dataset" />}>
          {analytics.status_distribution.length ? (
            <OutcomeBars data={analytics.status_distribution} />
          ) : (
            <p className="py-8 text-center text-sm text-slate-500">This dataset has no recorded status column.</p>
          )}
          {analytics.predicted_vs_recorded && (
            <p className="mt-4 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">{analytics.predicted_vs_recorded.note}</p>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Industry distribution" subtitle="Top market tags (a company can carry several)" actions={<SourceTag source="dataset" />}>
          <DistributionBars data={analytics.industry_distribution} color="#2a78d6" />
        </Card>
        <Card title="Funding distribution" subtitle={`Total reported: ${formatUsd(funding.total)} · median of non-zero: ${formatUsd(funding.median_nonzero)}`} actions={<SourceTag source="dataset" />}>
          <DistributionBars data={analytics.funding.buckets} color="#256abf" />
          {funding.by_status.length > 0 && (
            <table className="mt-4 w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500">
                  <th className="pb-1 font-medium">Recorded status</th>
                  <th className="pb-1 text-right font-medium">With funding</th>
                  <th className="pb-1 text-right font-medium">Median</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {funding.by_status.map((row) => (
                  <tr key={row.status}>
                    <td className="py-1.5 text-slate-700">{row.status}</td>
                    <td className="num py-1.5 text-right">{row.count}</td>
                    <td className="num py-1.5 text-right font-medium">{formatUsd(row.median)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Startups by batch year and recorded status" subtitle="Recent batches had less time to exit or fail before the data was collected" actions={<SourceTag source="dataset" />}>
          <YearStatusChart data={analytics.year_distribution} />
        </Card>
        <Card title="Top cities" actions={<SourceTag source="dataset" />}>
          <DistributionBars data={analytics.city_distribution} color="#256abf" />
        </Card>
      </div>

      <Card
        title="Model performance summary"
        subtitle={`${model.model_name} · trained on ${model.train_rows} companies, evaluated on ${model.test_rows} held-out companies`}
        actions={
          <Link to="/analytics" className="btn-ghost text-xs">
            Full evaluation <ArrowRight size={14} aria-hidden />
          </Link>
        }
      >
        <div className="grid gap-4 text-sm sm:grid-cols-3 lg:grid-cols-6">
          {[
            ['Accuracy', formatPct(holdout.accuracy)],
            ['Balanced accuracy', formatPct(holdout.balanced_accuracy)],
            ['Macro F1', holdout.f1_macro.toFixed(3)],
            ['Macro precision', holdout.precision_macro.toFixed(3)],
            ['ROC-AUC', holdout.roc_auc_ovr_macro.toFixed(3)],
            ['Log-loss', holdout.log_loss.toFixed(3)],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-slate-500">{label}</p>
              <p className="num mt-0.5 text-lg font-semibold text-navy-900">{value}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
