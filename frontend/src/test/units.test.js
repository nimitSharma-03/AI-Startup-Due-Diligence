import { describe, expect, it } from 'vitest'
import { formatPct, formatUsd, priorsFrom } from '../lib/format'
import { checkUploadFile, validatePrediction } from '../lib/validation'

const SCHEMA = [{ name: 'year', min: 1990, max: 2027 }]
const blank = { year: '', total_funding: '', city: '', markets: '' }

describe('formatting', () => {
  it('formats compact USD amounts', () => {
    expect(formatUsd(1_500_000)).toBe('$1.5M')
    expect(formatUsd(2_000_000)).toBe('$2M')
    expect(formatUsd(750)).toBe('$750')
    expect(formatUsd(null)).toBe('—')
  })
  it('formats percentages', () => {
    expect(formatPct(0.1379)).toBe('13.8%')
    expect(formatPct(undefined)).toBe('—')
  })
  it('recovers base rates from probabilities and lifts', () => {
    const priors = priorsFrom({
      probabilities: { Operating: 0.5, Exited: 0.26, Dead: 0.24 },
      lift_vs_base_rate: { Operating: 0.5 / 0.73, Exited: 2, Dead: 0.24 / 0.14 },
    })
    expect(priors.Exited).toBeCloseTo(0.13)
    expect(priors.Dead).toBeCloseTo(0.14)
  })
})

describe('prediction form validation', () => {
  it('requires a four-digit year in range', () => {
    expect(validatePrediction(blank, SCHEMA).year).toMatch(/required/)
    expect(validatePrediction({ ...blank, year: '12' }, SCHEMA).year).toMatch(/four-digit/)
    expect(validatePrediction({ ...blank, year: '1800' }, SCHEMA).year).toMatch(/between/)
    expect(validatePrediction({ ...blank, year: '2012' }, SCHEMA)).toEqual({})
  })
  it('accepts common money formats and rejects others', () => {
    for (const ok of ['1500000', '1.5M', '$2,000,000', '750k']) {
      expect(validatePrediction({ ...blank, year: '2012', total_funding: ok }, SCHEMA).total_funding).toBeUndefined()
    }
    expect(validatePrediction({ ...blank, year: '2012', total_funding: '-5' }, SCHEMA).total_funding).toBeDefined()
    expect(validatePrediction({ ...blank, year: '2012', total_funding: 'lots' }, SCHEMA).total_funding).toBeDefined()
  })
  it('limits market tags to ten', () => {
    const markets = Array.from({ length: 11 }, (_, i) => `m${i}`).join(',')
    expect(validatePrediction({ ...blank, year: '2012', markets }, SCHEMA).markets).toBeDefined()
  })
})

describe('upload file checks', () => {
  it('accepts CSV files within the size limit', () => {
    expect(checkUploadFile(new File(['a,b\n1,2'], 'data.csv'))).toBeNull()
  })
  it('rejects other types, empty files and missing files', () => {
    expect(checkUploadFile(new File(['x'], 'data.xlsx'))).toMatch(/csv/i)
    expect(checkUploadFile(new File([], 'empty.csv'))).toMatch(/empty/)
    expect(checkUploadFile(undefined)).toMatch(/Choose/)
  })
})
