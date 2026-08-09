import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://ai-startup-due-diligence.onrender.com',
  timeout: 30000,
})

function messageFrom(error) {
  return error.response?.data?.error || error.message || 'Something went wrong.'
}

export async function getDashboardData() {
  try {
    const [health, modelInfo, metrics] = await Promise.all([
      api.get('/health'), api.get('/model-info'), api.get('/metrics'),
    ])
    return { health: health.data, modelInfo: modelInfo.data, metrics: metrics.data }
  } catch (error) { throw new Error(messageFrom(error), { cause: error }) }
}

export async function predictStartup(data) {
  try { return (await api.post('/predict', { data })).data }
  catch (error) { throw new Error(messageFrom(error), { cause: error }) }
}

export async function predictCsv(file) {
  const formData = new FormData(); formData.append('file', file)
  try { return (await api.post('/predict/csv', formData)).data }
  catch (error) { throw new Error(messageFrom(error), { cause: error }) }
}

export async function generateDueDiligenceReport(file, rowIndex) {
  const formData = new FormData(); formData.append('file', file); formData.append('row_index', String(rowIndex))
  try { return await api.post('/reports/generate', formData, { responseType: 'blob', timeout: 120000 }) }
  catch (error) { throw new Error(messageFrom(error), { cause: error }) }
}

export async function getReportCompanies(file) {
  const formData = new FormData(); formData.append('file', file)
  try { return (await api.post('/reports/companies', formData)).data }
  catch (error) { throw new Error(messageFrom(error), { cause: error }) }
}
