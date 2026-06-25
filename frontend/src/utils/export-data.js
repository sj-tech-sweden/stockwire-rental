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
