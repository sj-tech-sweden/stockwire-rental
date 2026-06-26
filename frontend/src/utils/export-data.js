function normalizeExportValue(value) {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value) || (value && typeof value === 'object')) return JSON.stringify(value)
  return String(value)
}

export function collectExportColumns(rows) {
  const columns = []
  const seen = new Set()
  for (const row of rows || []) {
    if (!row || typeof row !== 'object') continue
    for (const key of Object.keys(row)) {
      if (seen.has(key)) continue
      seen.add(key)
      columns.push(key)
    }
  }
  return columns
}

function hasDisplayValue(value) {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim().length > 0
  return true
}

function firstDisplayValue(...values) {
  for (const value of values) {
    if (hasDisplayValue(value)) return value
  }
  return ''
}

export function enrichInventoryExportRows(entity, rows, options = {}) {
  const normalizedRows = Array.isArray(rows) ? rows.filter(row => row && typeof row === 'object') : []
  if (String(entity || '').toLowerCase() !== 'devices') return normalizedRows

  const productById = options.productById instanceof Map ? options.productById : new Map()
  const zoneById = options.zoneById instanceof Map ? options.zoneById : new Map()

  return normalizedRows.map(row => {
    const product = productById.get(Number(row.product_id || 0))
    const zone = zoneById.get(Number(row.location_zone_id || 0))
    return {
      ...row,
      product_name: firstDisplayValue(row.product_name, product?.name),
      location_name: firstDisplayValue(row.location_name, zone?.name),
      location_code: firstDisplayValue(row.location_code, zone?.code),
    }
  })
}

export function serializeRowsToCsv(rows) {
  const normalizedRows = Array.isArray(rows) ? rows.filter(row => row && typeof row === 'object') : []
  const columns = collectExportColumns(normalizedRows)
  if (!columns.length) return ''

  const isAllowedNegativeNumber = value => /^-\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value)
  const shouldSanitizeForSpreadsheet = value => {
    if (!value) return false
    const firstChar = value[0]
    if (firstChar === '-' && isAllowedNegativeNumber(value)) return false
    return /^[=+@\t\r-]/.test(firstChar)
  }

  const escapeCsv = (value) => {
    const normalized = normalizeExportValue(value)
    const sanitized = shouldSanitizeForSpreadsheet(normalized) ? `'${normalized}` : normalized
    if (/[",\n\r]/.test(sanitized)) return `"${sanitized.replace(/"/g, '""')}"`
    return sanitized
  }

  const header = columns.map(escapeCsv).join(',')
  const dataRows = normalizedRows.map(row => columns.map(column => escapeCsv(row[column])).join(','))
  return `${[header, ...dataRows].join('\n')}\n`
}

export function serializeRowsToJson(rows) {
  const normalizedRows = Array.isArray(rows) ? rows.filter(row => row && typeof row === 'object') : []
  return JSON.stringify(normalizedRows, null, 2)
}
