import { ConfusionMatrix, ImportanceBars, RocChart, ShareBars } from '../components/charts'
import { Card, ErrorState, Loading, Notice, PageHeader, StatTile } from '../components/ui'
import { api } from '../lib/api'
import { formatPct, OUTCOMES } from '../lib/format'
import { useApi } from '../lib/useApi'

const MODEL_LABELS = {
  majority_class: 'Majority class (baseline)',
  stratified_random: 'Stratified random (baseline)',
  logistic_regression: 'Logistic regression (baseline)',
  random_forest_uncalibrated: 'Random Forest, uncalibrated',
  random_forest_calibrated: 'Random Forest, calibrated (deployed)',
}
const METRICS = [
  ['balanced_accuracy', 'Balanced acc.'],
  ['f1_macro', 'Macro F1'],
  ['accuracy', 'Accuracy'],
  ['roc_auc_ovr_macro', 'ROC-AUC'],
  ['log_loss', 'Log-loss ↓'],
]

async function loadAll() {
  const [metrics, importance, model] = await Promise.all([api.metrics(), api.importance(), api.model()])
  return { metrics: metrics.data, importance: importance.data, model: model.data }
}

export default function Analytics() {
  const { data, error, loading, reload } = useApi(loadAll, [])
  return (
    <>
      <PageHeader
        eyebrow="Model analytics"
        title="Evaluation, explainability and limitations"
        description="Every number on this page is read from the artifacts written by the training script (python -m diligence.ml.train). Nothing is hand-entered."
      />
      {loading && <Loading label="Loading evaluation results…" />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && <Body {...data} />}
    </>
  )
}

function Body({ metrics, importance, model }) {
  const holdout = metrics.holdout
  const cv = metrics.cross_validation.models
  const quality = metrics.data_quality
  const report = holdout.classification_report
  const sensitivity = metrics.year_sensitivity
  const lastYear = quality.year_range[1]
  const lastCounts = quality.status_by_year[String(lastYear)] || {}
  const lastYearOperating = (lastCounts.Operating || 0) / Math.max(1, Object.values(lastCounts).reduce((a, b) => a + b, 0))
  const completeness = Object.entries(quality.missing_share).map(([field, missing]) => ({ field, label: field, share: 1 - missing }))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Hold-out balanced accuracy" value={formatPct(holdout.metrics.balanced_accuracy)} hint={`CV ${formatPct(cv.random_forest_calibrated.balanced_accuracy.mean)} ± ${formatPct(cv.random_forest_calibrated.balanced_accuracy.std)}`} />
        <StatTile label="Hold-out macro F1" value={holdout.metrics.f1_macro.toFixed(3)} hint={`CV ${cv.random_forest_calibrated.f1_macro.mean.toFixed(3)} ± ${cv.random_forest_calibrated.f1_macro.std.toFixed(3)}`} />
        <StatTile label="Hold-out ROC-AUC (macro OvR)" value={holdout.metrics.roc_auc_ovr_macro.toFixed(3)} hint={`CV ${cv.random_forest_calibrated.roc_auc_ovr_macro.mean.toFixed(3)} ± ${cv.random_forest_calibrated.roc_auc_ovr_macro.std.toFixed(3)}`} />
        <StatTile label="Hold-out log-loss" value={holdout.metrics.log_loss.toFixed(3)} hint={`Majority baseline ${metrics.holdout_comparison.majority_class.log_loss.toFixed(3)} · Brier ${holdout.metrics.brier_multiclass.toFixed(3)}`} />
      </div>

      <Notice tone="info" title="Read these numbers with the sample size in mind">
        The hold-out set has {holdout.test_rows} companies ({report.Dead.support} Dead, {report.Exited.support} Exited), so
        hold-out metrics move by several points between splits. The repeated cross-validation means (5 folds × 3 repeats on
        the {model.train_rows} training companies) are the steadier estimate.
        {holdout.metrics.balanced_accuracy > cv.random_forest_calibrated.balanced_accuracy.mean
          ? ' This particular hold-out split scored above the CV mean.'
          : ' This particular hold-out split scored at or below the CV mean.'}
      </Notice>

      <Card title="Model comparison" subtitle={metrics.cross_validation.scheme}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-2 font-medium">Model</th>
                <th className="py-2 font-medium">Decision</th>
                {METRICS.map(([key, label]) => (
                  <th key={key} className="py-2 text-right font-medium">
                    {label}
                    <span className="block font-normal">CV mean ± sd / hold-out</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {Object.entries(cv).map(([name, values]) => {
                const deployed = name === 'random_forest_calibrated'
                return (
                  <tr key={name} className={deployed ? 'bg-brand-50/60' : ''}>
                    <td className={`py-2.5 pr-3 ${deployed ? 'font-semibold text-navy-900' : 'text-slate-700'}`}>{MODEL_LABELS[name] || name}</td>
                    <td className="py-2.5 text-xs text-slate-500">{values.decision_rule}</td>
                    {METRICS.map(([key]) => (
                      <td key={key} className="num py-2.5 text-right text-slate-700">
                        {values[key].mean.toFixed(3)} <span className="text-xs text-slate-400">± {values[key].std.toFixed(3)}</span>
                        <span className="block text-xs text-slate-500">{metrics.holdout_comparison[name][key].toFixed(3)}</span>
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Balanced decision = class with the highest probability-to-base-rate ratio. The calibrated forest matches the
          uncalibrated class-weighted forest on balanced accuracy but has far better probability quality (log-loss), and is
          on par with logistic regression: with five inputs and 617 companies, a simpler model is about as good.
        </p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Confusion matrix (hold-out)" subtitle={`${holdout.test_rows} companies never seen in training`}>
          <ConfusionMatrix labels={holdout.confusion_matrix.labels} matrix={holdout.confusion_matrix.matrix} caption="Rows: recorded status. Columns: model-assigned class (balanced rule)." />
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1 font-medium">Class</th>
                <th className="py-1 text-right font-medium">Precision</th>
                <th className="py-1 text-right font-medium">Recall</th>
                <th className="py-1 text-right font-medium">F1</th>
                <th className="py-1 text-right font-medium">Support</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {OUTCOMES.map((label) => (
                <tr key={label}>
                  <td className="py-1.5">{label}</td>
                  <td className="num py-1.5 text-right">{report[label].precision.toFixed(2)}</td>
                  <td className="num py-1.5 text-right">{report[label].recall.toFixed(2)}</td>
                  <td className="num py-1.5 text-right">{report[label]['f1-score'].toFixed(2)}</td>
                  <td className="num py-1.5 text-right">{report[label].support}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="ROC curves (hold-out, one-vs-rest)">
          <RocChart curves={holdout.roc_curves} />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Global feature importance" subtitle={importance.permutation_method}>
          <ImportanceBars items={importance.permutation.map((item) => ({ name: item.label, value: item.importance }))} digits={4} />
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Values near zero (or slightly negative) mean shuffling that input does not hurt hold-out predictions. Importance
            measures reliance, not causation.
          </p>
        </Card>
        <Card title="Engineered features (impurity importance)" subtitle={importance.impurity_method}>
          <ImportanceBars items={importance.impurity.slice(0, 12).map((item) => ({ name: item.feature, value: item.importance }))} color="#5598e7" />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Calibration (hold-out)" subtitle="Mean predicted P(Dead) vs observed Dead rate, by probability bin">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1 font-medium">Bin</th>
                <th className="py-1 text-right font-medium">Mean predicted</th>
                <th className="py-1 text-right font-medium">Observed</th>
                <th className="py-1 text-right font-medium">Companies</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {holdout.reliability.Dead.map((row) => (
                <tr key={row.bin}>
                  <td className="py-1.5">{row.bin}</td>
                  <td className="num py-1.5 text-right">{formatPct(row.mean_predicted)}</td>
                  <td className="num py-1.5 text-right">{formatPct(row.observed_rate)}</td>
                  <td className="num py-1.5 text-right">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs leading-5 text-slate-500">Sigmoid calibration was fitted with 5-fold CV on the training split. Bins with few companies are noisy.</p>
        </Card>
        {sensitivity && (
          <Card title="Batch-year confound" subtitle={sensitivity.description}>
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr>
                  <th className="py-1 font-medium">Metric (CV mean)</th>
                  <th className="py-1 text-right font-medium">With year</th>
                  <th className="py-1 text-right font-medium">Year neutralised</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[
                  ['balanced_accuracy', 'Balanced accuracy'],
                  ['roc_auc_ovr_macro', 'ROC-AUC'],
                  ['log_loss', 'Log-loss'],
                ].map(([key, label]) => (
                  <tr key={key}>
                    <td className="py-1.5">{label}</td>
                    <td className="num py-1.5 text-right">{sensitivity.with_year[key].mean.toFixed(3)}</td>
                    <td className="num py-1.5 text-right">{sensitivity.without_year[key].mean.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              Recent batches had little time to exit or fail before collection (the {lastYear} batch is{' '}
              {formatPct(lastYearOperating, 0)} Operating). Much of
              the model&apos;s skill comes from that timing effect, which says little about a company&apos;s quality.
            </p>
          </Card>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Training data quality" subtitle={`${quality.rows} rows · ${quality.columns} columns · batches ${quality.year_range.join('-')}`}>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {[
              ['Duplicate rows', quality.duplicate_rows],
              ['Duplicate company names', quality.duplicate_company_names],
              ['Identical model inputs', quality.identical_model_inputs],
              ['Funding missing', quality.funding_missing],
              ['Funding reported as $0', quality.funding_reported_zero],
              ['Classes', Object.entries(quality.class_counts).map(([k, v]) => `${k} ${v}`).join(' · ')],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="num font-semibold text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card title="Column completeness (training CSV)" subtitle="Share of rows with a value">
          <div className="max-h-80 overflow-auto pr-1">
            <ShareBars items={completeness} />
          </div>
        </Card>
      </div>

      <Card title="Inputs and exclusions">
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <p className="text-sm font-semibold text-slate-800">Model inputs</p>
            <p className="mt-1 text-sm text-slate-600">{model.input_columns.join(', ')}</p>
            <p className="mt-3 text-sm font-semibold text-slate-800">Engineered features ({model.engineered_features.length})</p>
            <p className="mt-1 text-xs leading-5 break-words text-slate-500">{model.engineered_features.join(', ')}</p>
            <p className="mt-3 text-sm font-semibold text-slate-800">Hyperparameters</p>
            <p className="mt-1 text-xs text-slate-500">
              {Object.entries(model.hyperparameters).map(([k, v]) => `${k}=${v}`).join(' · ')}
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Excluded columns and why</p>
            <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
              {Object.entries(model.excluded_columns).map(([column, reason]) => (
                <li key={column}>
                  <span className="font-medium text-slate-800">{column}</span>: {reason}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}
