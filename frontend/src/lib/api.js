import axios from 'axios'

// Same-origin by default: the Flask service serves both the API and this app.
// Set VITE_API_BASE_URL only when the API is hosted on a different origin.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const client = axios.create({ baseURL: `${API_BASE_URL}/api`, timeout: 60000 })

export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

async function blobErrorMessage(data) {
  try {
    return JSON.parse(await data.text())?.error
  } catch {
    return null
  }
}

async function normalize(error) {
  if (error.response) {
    let body = error.response.data?.error
    if (!body && error.response.data instanceof Blob) body = await blobErrorMessage(error.response.data)
    return new ApiError(body?.message || `Request failed (${error.response.status}).`, {
      status: error.response.status,
      code: body?.code,
      details: body?.details,
    })
  }
  if (error.code === 'ECONNABORTED') {
    return new ApiError('The server took too long to respond. The free hosting tier may be waking up; please retry.', { code: 'timeout' })
  }
  return new ApiError('Could not reach the server. Check your connection and try again.', { code: 'network' })
}

async function call(promise) {
  try {
    const response = await promise
    return response.data
  } catch (error) {
    throw await normalize(error)
  }
}

const withDataset = (datasetId, params = {}) =>
  datasetId && datasetId !== 'reference' ? { ...params, dataset: datasetId } : params

export const api = {
  health: () => call(client.get('/health')),
  model: () => call(client.get('/model')),
  metrics: () => call(client.get('/model/metrics')),
  importance: () => call(client.get('/model/feature-importance')),
  analytics: (datasetId) => call(client.get('/analytics', { params: withDataset(datasetId) })),
  startups: (datasetId, params) => call(client.get('/startups', { params: withDataset(datasetId, params) })),
  facets: (datasetId) => call(client.get('/startups/facets', { params: withDataset(datasetId) })),
  startup: (datasetId, id) => call(client.get(`/startups/${encodeURIComponent(id)}`, { params: withDataset(datasetId) })),
  predict: (data) => call(client.post('/predict', { data })),
  validateDataset: (file) => {
    const form = new FormData()
    form.append('file', file)
    return call(client.post('/datasets/validate', form))
  },
  uploadDataset: (file) => {
    const form = new FormData()
    form.append('file', file)
    return call(client.post('/datasets', form))
  },
  deleteDataset: (id) => call(client.delete(`/datasets/${encodeURIComponent(id)}`)),
  async downloadReport(datasetId, startupId) {
    try {
      const response = await client.get(`/startups/${encodeURIComponent(startupId)}/report.pdf`, {
        params: withDataset(datasetId),
        responseType: 'blob',
        timeout: 120000,
      })
      return { blob: response.data, filename: filenameFrom(response, 'Due_Diligence_Report.pdf') }
    } catch (error) {
      throw await normalize(error)
    }
  },
}

export function reportUrl(datasetId, startupId) {
  const query = new URLSearchParams(withDataset(datasetId)).toString()
  return `${API_BASE_URL}/api/startups/${encodeURIComponent(startupId)}/report.pdf${query ? `?${query}` : ''}`
}

export function exportUrl(datasetId, params = {}) {
  const clean = Object.fromEntries(Object.entries(withDataset(datasetId, params)).filter(([, v]) => v !== '' && v != null))
  const query = new URLSearchParams(clean).toString()
  return `${API_BASE_URL}/api/startups/export.csv${query ? `?${query}` : ''}`
}

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function filenameFrom(response, fallback) {
  const disposition = response?.headers?.['content-disposition'] || ''
  return disposition.match(/filename="?([^";]+)"?/)?.[1] || fallback
}
