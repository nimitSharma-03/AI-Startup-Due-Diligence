const MONEY = /^\$?\s*\d[\d,]*(\.\d+)?\s*(k|m|mm|b|bn)?$/i
const MAX_UPLOAD_MB = 5

/** Client-side mirror of the API's validation rules for the prediction form. */
export function validatePrediction(values, schema) {
  const errors = {}
  const spec = Object.fromEntries((schema || []).map((field) => [field.name, field]))
  const year = values.year.trim()
  if (!year) errors.year = 'Batch year is required.'
  else if (!/^\d{4}$/.test(year)) errors.year = 'Enter a four-digit year.'
  else if (spec.year && (Number(year) < spec.year.min || Number(year) > spec.year.max)) errors.year = `Year must be between ${spec.year.min} and ${spec.year.max}.`
  if (values.total_funding.trim() && !MONEY.test(values.total_funding.trim())) errors.total_funding = 'Enter an amount such as 1500000, 1.5M or 750k.'
  if (values.city.length > 100) errors.city = 'City must be at most 100 characters.'
  const markets = values.markets.split(',').map((m) => m.trim()).filter(Boolean)
  if (markets.length > 10) errors.markets = 'Enter at most 10 market tags.'
  return errors
}

export function checkUploadFile(file) {
  if (!file) return 'Choose a file.'
  if (!/\.csv$/i.test(file.name)) return 'Only .csv files are supported.'
  if (file.size === 0) return 'The file is empty.'
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `The file is larger than ${MAX_UPLOAD_MB} MB.`
  return null
}

export { MAX_UPLOAD_MB }
