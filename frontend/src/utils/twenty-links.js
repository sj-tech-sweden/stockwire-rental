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
  people: 'person',
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

export function getTwentyCompanyUrl(company, config) {
  if (String(company?.external_source || '').trim().toLowerCase() !== 'twenty') return null
  return getTwentyRecordUrl('companies', company?.external_reference, config?.base_url)
}

export function getTwentyPersonUrl(person, config) {
  if (String(person?.external_source || '').trim().toLowerCase() !== 'twenty') return null
  return getTwentyRecordUrl('people', person?.external_reference, config?.base_url)
}
