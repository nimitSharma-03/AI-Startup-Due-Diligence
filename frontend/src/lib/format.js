export function formatUsd(value, { compact = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (!compact) return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
  const abs = Math.abs(value)
  for (const [limit, suffix] of [[1e9, 'B'], [1e6, 'M'], [1e3, 'K']]) {
    if (abs >= limit) return `$${(value / limit).toFixed(1).replace(/\.0$/, '')}${suffix}`
  }
  return `$${Math.round(value).toLocaleString('en-US')}`
}

export function formatPct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return Number(value).toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export function formatRatio(value) {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(2)}×`
}

export const OUTCOMES = ['Operating', 'Exited', 'Dead']
export const OUTCOME_COLORS = { Operating: '#2a78d6', Exited: '#1baf7a', Dead: '#eb6834' }
export const OUTCOME_HELP = {
  Operating: 'Still operating when the data was collected',
  Exited: 'Acquired or went public',
  Dead: 'Shut down',
}

/** Recover the training base rates from a prediction's probabilities and lifts. */
export function priorsFrom(prediction) {
  return Object.fromEntries(
    OUTCOMES.map((label) => [label, prediction.lift_vs_base_rate[label] ? prediction.probabilities[label] / prediction.lift_vs_base_rate[label] : 0]),
  )
}
