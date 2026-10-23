import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../App'
import { DatasetProvider } from '../lib/dataset'

const MODEL = {
  model_name: 'Calibrated Random Forest',
  classes: ['Dead', 'Exited', 'Operating'],
  class_priors: { Dead: 0.138, Exited: 0.13, Operating: 0.732 },
  train_rows: 493,
  test_rows: 124,
  holdout: { accuracy: 0.69, balanced_accuracy: 0.727, f1_macro: 0.614, precision_macro: 0.6, roc_auc_ovr_macro: 0.887, log_loss: 0.518 },
  cross_validation: { balanced_accuracy: { mean: 0.6, std: 0.05 }, roc_auc_ovr_macro: { mean: 0.83, std: 0.02 } },
  schema: [
    { name: 'year', label: 'Y Combinator batch year', min: 1990, max: 2027, help: 'Year' },
    { name: 'session', label: 'Batch session', options: ['Winter', 'Summer'] },
    { name: 'total_funding', label: 'Total funding raised (USD)', help: 'Funding' },
    { name: 'city', label: 'Headquarters city' },
    { name: 'markets', label: 'Markets / industries', help: 'Tags' },
  ],
}
const PREDICTION = {
  predicted_outcome: 'Operating',
  predicted_probability: 0.9,
  most_likely_outcome: 'Operating',
  probabilities: { Dead: 0.03, Exited: 0.07, Operating: 0.9 },
  lift_vs_base_rate: { Dead: 0.22, Exited: 0.54, Operating: 1.23 },
  failure_signal: { level: 'Lower', ratio_to_base_rate: 0.22, description: 'below' },
}
const ROWS = [
  { id: '3', row_number: 4, name: 'Zencoder', year: 2010, session: 'Winter', city: 'San Francisco', total_funding: 2e6, markets: ['SaaS'], status: 'Exited', scorable: true, issues: {}, prediction: { predicted_outcome: 'Exited', probabilities: { Dead: 0.05, Exited: 0.37, Operating: 0.58 }, failure_signal: 'Lower' } },
  { id: '7', row_number: 8, name: 'Acme', year: 2012, session: null, city: null, total_funding: null, markets: [], status: 'Dead', scorable: true, issues: {}, prediction: { predicted_outcome: 'Dead', probabilities: { Dead: 0.4, Exited: 0.1, Operating: 0.5 }, failure_signal: 'Elevated' } },
]

vi.mock('../lib/api', async (importOriginal) => {
  const original = await importOriginal()
  return {
    ...original,
    api: {
      model: vi.fn(async () => ({ data: MODEL })),
      predict: vi.fn(),
      startups: vi.fn(async (_id, params) => ({
        data: ROWS.filter((row) => !params?.q || row.name.toLowerCase().includes(params.q.toLowerCase())),
        meta: { page: 1, pages: 1, total: ROWS.length, page_size: 25 },
      })),
      facets: vi.fn(async () => ({ data: { industries: [], cities: [], statuses: [], years: [], predicted: [], signals: [] } })),
      analytics: vi.fn(),
    },
  }
})

const { api } = await import('../lib/api')

function renderAt(path) {
  return render(
    <DatasetProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </DatasetProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
})

describe('navigation', () => {
  it('renders the 404 page for unknown routes inside the layout', async () => {
    renderAt('/no-such-page')
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Startup Explorer/ }).length).toBeGreaterThan(0)
  })

  it('opens the methodology page directly', async () => {
    renderAt('/about')
    expect(await screen.findByRole('heading', { name: 'How the platform works' })).toBeInTheDocument()
    expect(await screen.findByText(/On 124 held-out companies/)).toBeInTheDocument()
  })
})

describe('prediction form', () => {
  it('blocks submission when the year is missing and shows an error', async () => {
    renderAt('/predict')
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /Run prediction/ }))
    expect(await screen.findByText('Batch year is required.')).toBeInTheDocument()
    expect(api.predict).not.toHaveBeenCalled()
  })

  it('submits valid input and renders the model result', async () => {
    api.predict.mockResolvedValue({
      data: {
        input: {},
        prediction: PREDICTION,
        explanation: [{ field: 'year', label: 'Batch year', value: '2012', contributions: { Dead: -0.02, Exited: -0.03, Operating: 0.05 } }],
        insights: { strengths: [], risks: [], limitations: ['No revenue data.'], considerations: ['Verify status.'], funding_context: null },
        summary: ['Example summary paragraph.'],
        warnings: [],
        missing_fields: ['city'],
      },
    })
    renderAt('/predict')
    const user = userEvent.setup()
    await user.type(await screen.findByLabelText(/Y Combinator batch year/), '2012')
    await user.type(screen.getByLabelText(/Total funding/), '1.5M')
    await user.click(screen.getByRole('button', { name: /Run prediction/ }))
    const result = await screen.findByTestId('prediction-result')
    expect(api.predict).toHaveBeenCalledWith(expect.objectContaining({ year: 2012, total_funding: '1.5M' }))
    expect(within(result).getByText('Example summary paragraph.')).toBeInTheDocument()
    expect(within(result).getByText(/Model inputs not provided/)).toBeInTheDocument()
  })

  it('maps server-side field errors back onto the form', async () => {
    const { ApiError } = await import('../lib/api')
    api.predict.mockRejectedValue(new ApiError('Some fields are invalid.', { status: 422, code: 'validation_failed', details: { city: 'must be at most 100 characters' } }))
    renderAt('/predict')
    const user = userEvent.setup()
    await user.type(await screen.findByLabelText(/Y Combinator batch year/), '2012')
    await user.click(screen.getByRole('button', { name: /Run prediction/ }))
    expect(await screen.findByText('must be at most 100 characters')).toBeInTheDocument()
  })
})

describe('explorer', () => {
  it('lists startups and links each row to its detail page', async () => {
    renderAt('/explorer')
    const table = await screen.findByTestId('startup-table')
    expect(within(table).getByRole('link', { name: 'Zencoder' })).toHaveAttribute('href', '/startups/3')
    expect(within(table).getByText('Acme')).toBeInTheDocument()
  })

  it('passes the search text to the API', async () => {
    renderAt('/explorer')
    const user = userEvent.setup()
    await screen.findByTestId('startup-table')
    await user.type(screen.getByTestId('explorer-search'), 'zen')
    await waitFor(() => expect(api.startups).toHaveBeenLastCalledWith('reference', expect.objectContaining({ q: 'zen' })))
    await waitFor(() => expect(screen.queryByText('Acme')).not.toBeInTheDocument())
  })
})
