const JSON_ENTITY_COLLECTIONS = [
  ['products', 'product'],
  ['devices', 'device'],
  ['locations', 'location'],
  ['zones', 'location'],
]

const ENTITY_TYPE_ALIASES = {
  product: 'product',
  products: 'product',
  device: 'device',
  devices: 'device',
  location: 'location',
  locations: 'location',
  zone: 'location',
  zones: 'location',
}

const METER_UNITS = ['m', 'meter', 'meters', 'metre', 'metres']
const CENTIMETER_UNITS = ['cm', 'centimeter', 'centimeters', 'centimetre', 'centimetres']

function normalizeEntityType(value) {
  if (value === null || value === undefined) return null
  const key = String(value).trim().toLowerCase()
  return ENTITY_TYPE_ALIASES[key] || null
}

function parseJsonRows(parsed) {
  if (Array.isArray(parsed)) return parsed
  if (Array.isArray(parsed?.items)) return parsed.items

  if (parsed && typeof parsed === 'object') {
    const composite = []
    for (const [key, entityType] of JSON_ENTITY_COLLECTIONS) {
      const items = parsed[key]
      if (!Array.isArray(items)) continue
      for (const item of items) {
        if (!item || typeof item !== 'object') continue
        composite.push({ ...item, __import_entity_type: entityType })
      }
    }
    if (composite.length) return composite
  }

  throw new Error('Import data must be an array, contain an items array, or include products/devices/locations/zones arrays')
}

function parseCsvRows(text) {
  const rows = []
  let row = []
  let value = ''
  let inQuotes = false

  const pushValue = () => {
    row.push(value)
    value = ''
  }

  const pushRow = () => {
    if (!row.length) return
    if (row.length === 1 && row[0] === '') {
      row = []
      return
    }
    rows.push(row)
    row = []
  }

  const normalizedText = String(text || '').replace(/\r\n?/g, '\n')
  for (let i = 0; i < normalizedText.length; i += 1) {
    const ch = normalizedText[i]

    if (ch === '"') {
      if (inQuotes && normalizedText[i + 1] === '"') {
        value += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (!inQuotes && ch === ',') {
      pushValue()
      continue
    }

    if (!inQuotes && ch === '\n') {
      pushValue()
      pushRow()
      continue
    }

    value += ch
  }

  pushValue()
  pushRow()

  if (rows.length < 2) {
    throw new Error('CSV must contain a header row and at least one data row')
  }

  const headers = rows[0].map(cell => String(cell || '').trim())
  if (!headers.some(Boolean)) {
    throw new Error('CSV header row is empty')
  }

  const parsedRows = []
  for (let i = 1; i < rows.length; i += 1) {
    const sourceRow = rows[i]
    if (sourceRow.every(cell => String(cell || '').trim() === '')) continue
    const rowObject = {}
    for (let col = 0; col < headers.length; col += 1) {
      const header = headers[col]
      if (!header) continue
      rowObject[header] = sourceRow[col] ?? ''
    }
    parsedRows.push(rowObject)
  }

  if (!parsedRows.length) {
    throw new Error('CSV does not contain any data rows')
  }

  return parsedRows
}

export function parseImportRows(text, filename = '') {
  const rawText = String(text || '')
  const preferCsv = /\.csv$/i.test(filename)
  const trimmedText = rawText.trimStart()
  const looksLikeJson = trimmedText.startsWith('{') || trimmedText.startsWith('[')
  let jsonError = null

  if (!preferCsv) {
    try {
      return parseJsonRows(JSON.parse(rawText))
    } catch (error) {
      jsonError = error
    }
  }

  try {
    return parseCsvRows(rawText)
  } catch (csvError) {
    if (jsonError && looksLikeJson) throw jsonError
    throw csvError
  }
}

function collectObjectKeys(obj, keys, prefix = '') {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return
  for (const [key, value] of Object.entries(obj)) {
    if (key.startsWith('__')) continue
    const path = prefix ? `${prefix}.${key}` : key
    keys.add(path)
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      collectObjectKeys(value, keys, path)
    }
  }
}

export function collectImportSourceKeys(rows) {
  const keys = new Set()
  for (const row of rows || []) {
    collectObjectKeys(row, keys)
  }
  return Array.from(keys)
}

export function getImportValueBySourceKey(row, sourceKey) {
  if (!row || !sourceKey) return undefined
  if (Object.prototype.hasOwnProperty.call(row, sourceKey)) return row[sourceKey]

  const path = String(sourceKey).split('.').map(part => part.trim()).filter(Boolean)
  if (!path.length) return undefined

  let current = row
  for (const part of path) {
    if (!current || typeof current !== 'object' || !(part in current)) return undefined
    current = current[part]
  }

  return current
}

export function resolveImportEntityType(row, fallbackEntityType = null) {
  const explicit = normalizeEntityType(row?.__import_entity_type)
  if (explicit) return explicit

  const candidates = [row?.entity_type, row?.entityType, row?.type]
  for (const candidate of candidates) {
    const resolved = normalizeEntityType(candidate)
    if (resolved) return resolved
  }

  return normalizeEntityType(fallbackEntityType)
}

function sourceKeyIndicatesMeters(sourceKey) {
  if (!sourceKey) return false
  const escapedUnits = METER_UNITS.map(unit => unit.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  return new RegExp(`(^|[._\\s])(${escapedUnits.join('|')})([._\\s]|$)`, 'i').test(String(sourceKey))
}

export function convertDimensionValueToCm(value, sourceKey = '') {
  if (value === null || value === undefined || value === '') return value

  const sourceIsMeters = sourceKeyIndicatesMeters(sourceKey)
  if (typeof value === 'number') {
    return sourceIsMeters ? value * 100 : value
  }

  const normalized = String(value).trim()
  const match = normalized.match(/^(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$/)
  if (!match) return value

  const amount = Number(match[1])
  if (Number.isNaN(amount)) return value

  const unit = String(match[2] || '').toLowerCase()
  if (METER_UNITS.includes(unit)) return amount * 100
  if (CENTIMETER_UNITS.includes(unit)) return amount
  if (!unit && sourceIsMeters) return amount * 100
  if (unit) return value
  return amount
}
