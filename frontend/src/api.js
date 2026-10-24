
const API_BASE_URL = 'http://localhost:8000'

async function fetchJSON(url, options = {}, fallbackMessage = 'Request failed.') {
  const response = await fetch(url, options)
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || fallbackMessage)
  }

  return data
}

function datasetURL(endpoint, datasetId = 'rainfall_surat') {
  const params = new URLSearchParams({ dataset_id: datasetId })
  return `${API_BASE_URL}${endpoint}?${params.toString()}`
}

export async function getDatasets() {
  const data = await fetchJSON(`${API_BASE_URL}/api/datasets`)
  return data.datasets ?? []
}

export async function getLatestHealthReport(datasetId = 'rainfall_surat') {
  return fetchJSON(datasetURL('/api/health/latest', datasetId))
}

export async function getHealthHistory(datasetId = 'rainfall_surat') {
  return fetchJSON(datasetURL('/api/health/history', datasetId))
}

export async function runMonitor(datasetId = 'rainfall_surat') {
  return fetchJSON(
    datasetURL('/api/monitor/run', datasetId),
    { method: 'POST' },
    'Monitoring run failed.',
  )
}

export async function getHealthComparison(datasetId = 'rainfall_surat') {
  return fetchJSON(datasetURL('/api/health/compare', datasetId))
}

export async function getMonitorStatus() {
  return fetchJSON(`${API_BASE_URL}/api/monitor/status`)
}

export async function getHealthTrends(datasetId = 'rainfall_surat') {
  return fetchJSON(datasetURL('/api/health/trends', datasetId))
}

export async function getReliability(datasetId = 'rainfall_surat') {
  return fetchJSON(datasetURL('/api/reliability', datasetId))
}

export async function getMandiPriceHistory(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) })
  return fetchJSON(
    `${API_BASE_URL}/api/prices/history?${params.toString()}`,
  )
}

export async function getMandiPriceChanges(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) })
  return fetchJSON(
    `${API_BASE_URL}/api/prices/changes?${params.toString()}`,
  )
}
