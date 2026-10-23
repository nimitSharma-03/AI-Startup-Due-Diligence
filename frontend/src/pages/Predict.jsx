import { RotateCcw, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { ContributionCard, IndicatorsGrid, LimitationsCard, PredictionCard, SummaryCard } from '../components/Analysis'
import { Card, ErrorState, Loading, Notice, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { validatePrediction } from '../lib/validation'

const EMPTY = { name: '', year: '', session: '', total_funding: '', city: '', markets: '' }
const EXAMPLE = { name: 'Example Analytics Co', year: '2011', session: 'Winter', total_funding: '1.2M', city: 'San Francisco', markets: 'SaaS, Analytics' }
export default function Predict() {
  const model = useApi(() => api.model(), [])
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState(null)
  const schema = model.data?.data?.schema

  const set = (key) => (event) => {
    setValues((previous) => ({ ...previous, [key]: event.target.value }))
    setErrors((previous) => ({ ...previous, [key]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = validatePrediction(values, schema)
    setErrors(found)
    setServerError(null)
    if (Object.keys(found).length) return
    setSubmitting(true)
    try {
      const payload = {
        name: values.name.trim() || undefined,
        year: Number(values.year),
        session: values.session || null,
        total_funding: values.total_funding.trim() || null,
        city: values.city.trim() || null,
        markets: values.markets,
      }
      const response = await api.predict(payload)
      setResult({ ...response.data, name: values.name.trim() || 'Submitted startup' })
    } catch (error) {
      if (error.code === 'validation_failed' && error.details) setErrors(error.details)
      setServerError(error)
      setResult(null)
    } finally {
      setSubmitting(false)
    }
  }

  const reset = () => {
    setValues(EMPTY)
    setErrors({})
    setResult(null)
    setServerError(null)
  }

  const field = (name) => schema?.find((item) => item.name === name)

  return (
    <>
      <PageHeader
        eyebrow="Prediction"
        title="Score a startup"
        description="Enter the attributes the model was trained on. Only batch year is required; anything left blank is treated as missing and disclosed in the result."
      />
      {model.loading && <Loading label="Loading model schema…" />}
      {model.error && <ErrorState error={model.error} onRetry={model.reload} />}
      {schema && (
        <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
          <Card title="Startup attributes" subtitle="Inputs match the model's training schema" className="h-fit xl:sticky xl:top-6">
            <form onSubmit={submit} noValidate className="space-y-4" aria-label="Prediction form">
              <Field id="name" label="Company name (optional, not used by the model)" error={errors.name}>
                <input id="name" className="input" value={values.name} onChange={set('name')} maxLength={100} />
              </Field>
              <Field id="year" label={`${field('year').label} *`} error={errors.year} help={field('year').help}>
                <input id="year" className="input" inputMode="numeric" value={values.year} onChange={set('year')} placeholder="e.g. 2012" aria-invalid={Boolean(errors.year)} />
              </Field>
              <Field id="session" label={field('session').label} error={errors.session}>
                <select id="session" className="input" value={values.session} onChange={set('session')}>
                  <option value="">Not provided</option>
                  {field('session').options.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </Field>
              <Field id="total_funding" label={field('total_funding').label} error={errors.total_funding} help={field('total_funding').help}>
                <input id="total_funding" className="input" value={values.total_funding} onChange={set('total_funding')} placeholder="e.g. 1.5M" aria-invalid={Boolean(errors.total_funding)} />
              </Field>
              <Field id="city" label={field('city').label} error={errors.city}>
                <input id="city" className="input" value={values.city} onChange={set('city')} placeholder="e.g. San Francisco" />
              </Field>
              <Field id="markets" label={field('markets').label} error={errors.markets} help={field('markets').help}>
                <input id="markets" className="input" value={values.markets} onChange={set('markets')} placeholder="e.g. SaaS, Analytics" />
              </Field>
              <div className="flex flex-wrap gap-2 pt-1">
                <button type="submit" className="btn-primary" disabled={submitting}>
                  <Sparkles size={15} aria-hidden /> {submitting ? 'Scoring…' : 'Run prediction'}
                </button>
                <button type="button" className="btn-secondary" onClick={() => setValues(EXAMPLE)}>
                  Fill example
                </button>
                <button type="button" className="btn-ghost" onClick={reset}>
                  <RotateCcw size={14} aria-hidden /> Reset
                </button>
              </div>
            </form>
          </Card>

          <div className="min-w-0 space-y-6" aria-live="polite">
            {serverError && !Object.keys(errors).length && <ErrorState error={serverError} />}
            {serverError?.code === 'validation_failed' && <Notice tone="warning" title="Please correct the highlighted fields.">{serverError.message}</Notice>}
            {!result && !serverError && (
              <Card>
                <div className="py-8 text-center text-sm text-slate-500">
                  <Sparkles className="mx-auto mb-3 text-brand-600" aria-hidden />
                  Results appear here: class probabilities, the failure-pattern signal, the inputs that drive the estimate, and
                  the information that is missing.
                </div>
              </Card>
            )}
            {result && (
              <div className="space-y-6" data-testid="prediction-result">
                <SummaryCard paragraphs={result.summary} />
                <PredictionCard prediction={result.prediction} />
                <ContributionCard explanation={result.explanation} defaultOutcome={result.prediction.predicted_outcome} />
                <IndicatorsGrid insights={result.insights} />
                <LimitationsCard insights={result.insights} missingFields={result.missing_fields} warnings={result.warnings} />
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

function Field({ id, label, error, help, children }) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      {children}
      {error ? (
        <p className="mt-1 text-xs text-red-700" role="alert">
          {error}
        </p>
      ) : (
        help && <p className="mt-1 text-xs text-slate-500">{help}</p>
      )}
    </div>
  )
}
