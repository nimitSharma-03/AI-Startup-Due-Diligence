import { Link } from 'react-router-dom'
import { Card, Notice, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { formatPct } from '../lib/format'
import { useApi } from '../lib/useApi'

function Section({ title, children }) {
  return (
    <Card title={title}>
      <div className="space-y-3 text-sm leading-6 text-slate-700">{children}</div>
    </Card>
  )
}

export default function About() {
  const { data } = useApi(() => api.model(), [])
  const model = data?.data
  return (
    <>
      <PageHeader
        eyebrow="About and methodology"
        title="How the platform works"
        description="What the system does, where its data comes from, how the model was built and evaluated, and what it cannot tell you."
      />
      <div className="space-y-6">
        <Notice tone="warning" title="Not financial advice">
          This is an educational and analytical project. It is not a regulated advisory service, and its outputs must not be
          used as the basis for investment decisions.
        </Notice>

        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Purpose">
            <p>
              The platform demonstrates an end-to-end due-diligence screening workflow: explore a portfolio of startups, score
              each against historical outcome patterns with a machine-learning model, inspect why the model says what it says,
              and export a company-specific PDF report that separates dataset facts from model estimates.
            </p>
          </Section>
          <Section title="Dataset provenance">
            <p>
              The reference data is <code>data/CleanStartups.csv</code>: 617 Y Combinator companies from batches 2005–2014
              with fields from public SeedDB and CrunchBase listings (name, description, batch, city, total funding, market
              tags, founders, investors, URLs) and a recorded status: Operating, Exited (acquired or IPO) or Dead.
            </p>
            <p>
              The original collection date is not documented in the repository. Because the latest batch is 2014, statuses
              and funding totals reflect roughly 2014–2015, not today. Companies with poor public documentation are more
              likely to be missing fields, and that missingness is itself correlated with failure.
            </p>
          </Section>
        </div>

        <Section title="Machine-learning methodology">
          <ol className="list-decimal space-y-2 pl-5">
            <li>
              <strong>Target.</strong> The recorded status (Operating / Exited / Dead). It is a snapshot status, not a forecast
              horizon or a financial return, so the model output is presented as outcome-class probabilities rather than an
              investment risk score.
            </li>
            <li>
              <strong>Inputs.</strong> Batch year, batch session, total funding (log-scaled, with a missing-value flag), city and
              market tags. Cities and tags that appear fewer than 10 times are grouped as &ldquo;other&rdquo;. Unknown values at
              prediction time fall into those groups instead of failing.
            </li>
            <li>
              <strong>Leakage control.</strong> The earlier version of this project trained on the row index, company name,
              logo and website URLs. Those are excluded, as are founder and investor listings, because their presence mostly
              measures how well a company was documented after the fact.
            </li>
            <li>
              <strong>Pipeline.</strong> A custom scikit-learn transformer and the classifier are saved as one pipeline, so the
              same code and fitted vocabularies are used in training and serving.
            </li>
            <li>
              <strong>Model.</strong> A class-weighted Random Forest (300 trees) tuned by 5-fold grid search on a stratified
              80% training split, then wrapped in sigmoid probability calibration.
            </li>
            <li>
              <strong>Decision rule.</strong> The assigned class is the one whose probability most exceeds its base rate.
              This optimises balanced accuracy, so the minority Exited and Dead outcomes are not swamped by the 73% Operating
              majority.
            </li>
            <li>
              <strong>Explanations.</strong> Global importance by permutation of each raw input on the hold-out set; per-company
              attributions by swapping each input for values from 50 typical training companies. Both describe model
              behaviour and say nothing about causation.
            </li>
          </ol>
        </Section>

        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Evaluation">
            {model ? (
              <p>
                On {model.test_rows} held-out companies: balanced accuracy {formatPct(model.holdout.balanced_accuracy)}, macro F1{' '}
                {model.holdout.f1_macro.toFixed(2)}, macro ROC-AUC {model.holdout.roc_auc_ovr_macro.toFixed(2)}. Repeated
                cross-validation: balanced accuracy {formatPct(model.cross_validation.balanced_accuracy.mean)} ±{' '}
                {formatPct(model.cross_validation.balanced_accuracy.std)}, ROC-AUC{' '}
                {model.cross_validation.roc_auc_ovr_macro.mean.toFixed(2)} ± {model.cross_validation.roc_auc_ovr_macro.std.toFixed(2)}.
              </p>
            ) : (
              <p>Loading live metrics…</p>
            )}
            <p>
              Baselines (majority class, stratified random and logistic regression) are evaluated the same way. The forest
              clearly beats the naive baselines and is on par with logistic regression.{' '}
              <Link to="/analytics" className="text-brand-700 hover:underline">
                See the full evaluation.
              </Link>
            </p>
          </Section>
          <Section title="Technical architecture">
            <ul className="list-disc space-y-1.5 pl-5">
              <li>React 19 + Vite + Tailwind CSS + Recharts single-page app.</li>
              <li>Flask REST API under <code>/api</code> (Gunicorn in production) with validation, consistent JSON errors and request logging.</li>
              <li>scikit-learn pipeline loaded once at start-up; predictions and explanations are computed per request.</li>
              <li>PDF reports rendered in memory with ReportLab and Matplotlib.</li>
              <li>Uploaded CSVs are parsed as text, held in memory for about two hours, and never written to disk or unpickled.</li>
              <li>One Docker web service on Render serves both the API and the built frontend.</li>
            </ul>
          </Section>
        </div>

        <Section title="Known limitations">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>617 companies from a single accelerator and era; results do not transfer to other populations.</li>
            <li>
              Batch year dominates because younger companies had less time to exit or fail. Neutralising it lowers
              cross-validated ROC-AUC substantially (see Model Analytics).
            </li>
            <li>Total funding is cumulative at collection time, so it partly reflects what happened after the batch.</li>
            <li>No revenue, burn, runway, valuation, team or traction data exists in the dataset; none is inferred.</li>
            <li>Probabilities are calibrated on a small sample; treat them as rough estimates.</li>
            <li>Uploaded datasets are temporary and disappear when the free hosting instance restarts.</li>
          </ul>
        </Section>

        <Section title="Intended use">
          <p>
            Learning, portfolio demonstration and exploratory screening. A real investment decision requires primary-source
            diligence: financial statements, legal review, customer references, market analysis and founder background checks.
          </p>
        </Section>
      </div>
    </>
  )
}
