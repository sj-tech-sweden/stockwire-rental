function normalizeTwentyBaseUrl(baseUrl) {
  const fallback = 'https://app.twenty.com'
  const raw = String(baseUrl || '').trim()
  if (!raw) return fallback
  try {
    const url = new URL(raw)
    if (url.hostname === 'api.twenty.com') {
      url.hostname = 'app.twenty.com'
    }
    url.pathname = ''
    url.search = ''
    url.hash = ''
    return url.toString().replace(/\/$/, '')
  } catch {
    return fallback
  }
}

function normalizeTwentyRecordId(recordId) {
  const value = String(recordId || '').trim()
  return value || null
}

const ENTITY_TYPE_MAP = {
  companies: 'company',
  opportunities: 'opportunity',
}

export function getTwentyRecordUrl(entityType, recordId, baseUrl) {
  const id = normalizeTwentyRecordId(recordId)
  if (!id) return null

  const entity = String(entityType || '').trim().toLowerCase()
  const mapped = ENTITY_TYPE_MAP[entity]
  if (!mapped) return null

  return `${normalizeTwentyBaseUrl(baseUrl)}/object/${mapped}/${encodeURIComponent(id)}`
}

export function getTwentyCustomerUrl(customer, config) {
  if (String(customer?.external_source || '').trim().toLowerCase() !== 'twenty') return null
  return getTwentyRecordUrl('companies', customer?.external_reference, config?.base_url)
}

export function getTwentyJobUrl(job, config) {
  if (String(job?.external_source || '').trim().toLowerCase() !== 'twenty') return null
  return getTwentyRecordUrl('opportunities', job?.external_reference, config?.base_url)
}
