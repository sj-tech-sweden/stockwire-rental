const DB_NAME = 'stockwire-offline'
const DB_VERSION = 1
const SNAPSHOT_STORE = 'snapshots'
const QUEUE_STORE = 'queue'
const BLOCKED_TEMP_PRODUCT_TTL_HOURS = 24

let orbitInitialized = false
let orbitAvailable = false

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)

    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(SNAPSHOT_STORE)) {
        db.createObjectStore(SNAPSHOT_STORE, { keyPath: 'key' })
      }
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, { keyPath: 'id' })
      }
    }

    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function withStore(storeName, mode, run) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode)
    const store = tx.objectStore(storeName)
    const result = run(store)
    tx.oncomplete = () => resolve(result)
    tx.onerror = () => reject(tx.error)
    tx.onabort = () => reject(tx.error)
  })
}

function putRequest(store, value) {
  return new Promise((resolve, reject) => {
    const req = store.put(toIndexedDbSafeValue(value))
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function toIndexedDbSafeValue(value) {
  try {
    return structuredClone(value)
  } catch {
    return toPlainValue(value)
  }
}

function toPlainValue(value, seen = new WeakMap()) {
  if (value === null || value === undefined) return value

  const valueType = typeof value
  if (valueType === 'string' || valueType === 'number' || valueType === 'boolean' || valueType === 'bigint') {
    return value
  }
  if (valueType === 'function' || valueType === 'symbol') {
    return undefined
  }

  if (value instanceof Date) {
    return value.toISOString()
  }

  if (Array.isArray(value)) {
    return value.map(item => toPlainValue(item, seen))
  }

  if (value instanceof Map) {
    const out = {}
    for (const [key, mapValue] of value.entries()) {
      out[String(key)] = toPlainValue(mapValue, seen)
    }
    return out
  }

  if (value instanceof Set) {
    return Array.from(value, item => toPlainValue(item, seen))
  }

  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: value.stack,
    }
  }

  if (valueType === 'object') {
    if (seen.has(value)) {
      return seen.get(value)
    }

    const out = {}
    seen.set(value, out)

    for (const [key, objectValue] of Object.entries(value)) {
      const normalized = toPlainValue(objectValue, seen)
      if (normalized !== undefined) {
        out[key] = normalized
      }
    }

    return out
  }

  return value
}

function getRequest(store, key) {
  return new Promise((resolve, reject) => {
    const req = store.get(key)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function getAllRequest(store) {
  return new Promise((resolve, reject) => {
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result || [])
    req.onerror = () => reject(req.error)
  })
}

function deleteRequest(store, key) {
  return new Promise((resolve, reject) => {
    const req = store.delete(key)
    req.onsuccess = () => resolve(true)
    req.onerror = () => reject(req.error)
  })
}

export async function initOrbitSync() {
  if (orbitInitialized) return orbitAvailable
  orbitInitialized = true

  try {
    const modules = await Promise.all([
      import('@orbit/data'),
      import('@orbit/memory'),
      import('@orbit/indexeddb'),
    ])
    orbitAvailable = modules.every(Boolean)
  } catch {
    orbitAvailable = false
  }

  return orbitAvailable
}

let _backendReachable = true
let _lastCheckTime = 0
const CHECK_INTERVAL_MS = 30000

export function isOnline() {
  if (typeof navigator === 'undefined') return true
  return navigator.onLine && _backendReachable
}

export async function checkBackendReachability() {
  const now = Date.now()
  if (now - _lastCheckTime < CHECK_INTERVAL_MS) {
    return _backendReachable
  }
  _lastCheckTime = now

  try {
    const response = await fetch('/api/v1/health', {
      method: 'HEAD',
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    _backendReachable = response.ok
  } catch {
    _backendReachable = false
  }
  return _backendReachable
}

export function setBackendReachable(reachable) {
  _backendReachable = reachable
}

export async function cacheSnapshot(key, payload) {
  await withStore(SNAPSHOT_STORE, 'readwrite', async (store) => {
    await putRequest(store, {
      key,
      payload,
      updatedAt: new Date().toISOString(),
    })
  })
}

export async function readSnapshot(key) {
  return withStore(SNAPSHOT_STORE, 'readonly', async (store) => {
    const row = await getRequest(store, key)
    return row?.payload ?? null
  })
}

export async function queueMutation(mutation) {
  const conflictPolicy = mutation.conflictPolicy || inferConflictPolicy(mutation)
  const resourceKey = mutation.resourceKey || inferResourceKey(mutation)
  const queued = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt: new Date().toISOString(),
    conflictPolicy,
    resourceKey,
    ...mutation,
  }

  await withStore(QUEUE_STORE, 'readwrite', async (store) => {
    await putRequest(store, queued)
  })

  return queued
}

export async function listQueuedMutations() {
  return withStore(QUEUE_STORE, 'readonly', async (store) => {
    const rows = await getAllRequest(store)
    return rows.sort((a, b) => String(a.createdAt || '').localeCompare(String(b.createdAt || '')))
  })
}

export async function removeQueuedMutation(id) {
  await withStore(QUEUE_STORE, 'readwrite', async (store) => {
    await deleteRequest(store, id)
  })
}

export async function clearQueuedMutations() {
  const rows = await listQueuedMutations()
  for (const row of rows) {
    if (row?.id) {
      await removeQueuedMutation(row.id)
    }
  }
}

export async function flushQueuedMutations(executor) {
  if (!isOnline()) return { flushed: 0, failed: 0, failedIds: [], deferred: 0, deferredIds: [], pruned: 0, prunedIds: [] }

  const pruneResult = await pruneStaleBlockedQueuedMutations()

  const { rows, supersededIds } = normalizeQueuedMutations(await listQueuedMutations())
  let flushed = 0
  let failed = 0
  const failedIds = []
  const tempProductIdMap = new Map()
  const pendingCreatedProductIds = []

  for (const id of supersededIds) {
    await removeQueuedMutation(id)
  }

  const deferredRows = []

  for (const row of rows) {
    const replayMutation = remapMutationForReplay(row, tempProductIdMap, pendingCreatedProductIds)
    if (hasUnresolvedTempProductReference(replayMutation)) {
      deferredRows.push(row)
      continue
    }
    try {
      const result = await executor(replayMutation)
      const createdProductId = extractCreatedProductId(replayMutation, result)
      if (createdProductId != null) {
        const tempId = extractQueuedTempProductId(row)
        if (tempId != null) {
          tempProductIdMap.set(tempId, createdProductId)
        } else {
          pendingCreatedProductIds.push(createdProductId)
        }
      }
      await removeQueuedMutation(row.id)
      flushed += 1
    } catch (error) {
      failed += 1
      if (row?.id) {
        failedIds.push(row.id)
      }
      if (Number(error?.response?.status || 0) === 401) {
        break
      }
    }
  }

  // Retry unresolved temp-id rows once product creations in this flush have been mapped.
  for (const row of deferredRows) {
    const replayMutation = remapMutationForReplay(row, tempProductIdMap, pendingCreatedProductIds)
    if (hasUnresolvedTempProductReference(replayMutation)) {
      continue
    }
    try {
      await executor(replayMutation)
      await removeQueuedMutation(row.id)
      flushed += 1
    } catch (error) {
      failed += 1
      if (row?.id) {
        failedIds.push(row.id)
      }
      if (Number(error?.response?.status || 0) === 401) {
        break
      }
    }
  }

  const deferredIds = deferredRows
    .map(row => row?.id)
    .filter(Boolean)
  return {
    flushed,
    failed,
    failedIds,
    deferred: deferredIds.length,
    deferredIds,
    pruned: pruneResult.pruned,
    prunedIds: pruneResult.prunedIds,
  }
}

export async function pruneStaleBlockedQueuedMutations({ maxAgeHours = BLOCKED_TEMP_PRODUCT_TTL_HOURS } = {}) {
  const rows = await listQueuedMutations()
  const maxAgeMs = Math.max(Number(maxAgeHours || 0), 0) * 60 * 60 * 1000
  const cutoff = Date.now() - maxAgeMs
  let pruned = 0
  const prunedIds = []

  for (const row of rows) {
    if (!row?.id) continue
    if (!mutationContainsTempProductReference(row)) continue
    const createdAtMs = toTimestamp(row?.createdAt)
    if (createdAtMs == null) continue
    if (createdAtMs > cutoff) continue
    await removeQueuedMutation(row.id)
    pruned += 1
    prunedIds.push(row.id)
  }

  return { pruned, prunedIds }
}

function remapMutationForReplay(row, tempProductIdMap, pendingCreatedProductIds) {
  const mutation = {
    ...row,
    data: cloneValue(row?.data),
    params: cloneValue(row?.params),
  }

  mutation.url = remapProductIdInUrl(String(mutation.url || ''), tempProductIdMap, pendingCreatedProductIds)
  mutation.data = remapProductIdsInPayload(mutation.data, tempProductIdMap, pendingCreatedProductIds)
  mutation.params = remapProductIdsInPayload(mutation.params, tempProductIdMap, pendingCreatedProductIds)

  return mutation
}

function cloneValue(value) {
  if (value == null) return value
  if (typeof value !== 'object') return value
  try {
    return structuredClone(value)
  } catch {
    return toPlainValue(value)
  }
}

function remapProductIdInUrl(url, tempProductIdMap, pendingCreatedProductIds) {
  const match = url.match(/^\/api\/v1\/inventory\/products\/(-\d+)(\/.*)?$/)
  if (!match) return url
  const mapped = resolveTempProductId(Number(match[1]), tempProductIdMap, pendingCreatedProductIds)
  if (mapped == null) return url
  const suffix = match[2] || ''
  return `/api/v1/inventory/products/${mapped}${suffix}`
}

function remapProductIdsInPayload(payload, tempProductIdMap, pendingCreatedProductIds) {
  if (!payload || typeof payload !== 'object') return payload

  if (typeof payload.product_id === 'number' && payload.product_id < 0) {
    const mapped = resolveTempProductId(payload.product_id, tempProductIdMap, pendingCreatedProductIds)
    if (mapped != null) payload.product_id = mapped
  }

  if (Array.isArray(payload.product_ids)) {
    payload.product_ids = payload.product_ids.map((value) => {
      if (typeof value !== 'number' || value >= 0) return value
      const mapped = resolveTempProductId(value, tempProductIdMap, pendingCreatedProductIds)
      return mapped != null ? mapped : value
    })
  }

  if (Array.isArray(payload.items)) {
    payload.items = payload.items.map((item) => remapProductIdsInPayload(item, tempProductIdMap, pendingCreatedProductIds) || item)
  }

  return payload
}

function resolveTempProductId(tempId, tempProductIdMap, pendingCreatedProductIds) {
  if (typeof tempId !== 'number' || tempId >= 0) return tempId
  if (tempProductIdMap.has(tempId)) {
    return tempProductIdMap.get(tempId)
  }
  if (pendingCreatedProductIds.length > 0) {
    const mapped = pendingCreatedProductIds.shift()
    tempProductIdMap.set(tempId, mapped)
    return mapped
  }
  return null
}

function extractCreatedProductId(mutation, result) {
  const method = String(mutation?.method || '').toLowerCase()
  const url = String(mutation?.url || '')
  if (method !== 'post' || url !== '/api/v1/inventory/products') return null
  const id = result?.data?.id
  return typeof id === 'number' ? id : null
}

function extractQueuedTempProductId(row) {
  const direct = Number(row?.clientTempId)
  if (Number.isFinite(direct) && direct < 0) return direct
  const metaTemp = Number(row?.meta?.tempProductId)
  if (Number.isFinite(metaTemp) && metaTemp < 0) return metaTemp
  const nested = Number(row?.meta?.clientTempId)
  if (Number.isFinite(nested) && nested < 0) return nested
  return null
}

function hasUnresolvedTempProductReference(mutation) {
  const url = String(mutation?.url || '')
  if (/\/api\/v1\/inventory\/products\/-\d+\//.test(url)) {
    return true
  }
  return payloadHasUnresolvedTempProductId(mutation?.data) || payloadHasUnresolvedTempProductId(mutation?.params)
}

function payloadHasUnresolvedTempProductId(payload) {
  if (!payload || typeof payload !== 'object') return false

  if (typeof payload.product_id === 'number' && payload.product_id < 0) {
    return true
  }

  if (Array.isArray(payload.product_ids) && payload.product_ids.some(value => typeof value === 'number' && value < 0)) {
    return true
  }

  if (Array.isArray(payload.items)) {
    return payload.items.some(item => payloadHasUnresolvedTempProductId(item))
  }

  return false
}

function mutationContainsTempProductReference(mutation) {
  const url = String(mutation?.url || '')
  if (/\/api\/v1\/inventory\/products\/-\d+\//.test(url)) {
    return true
  }
  if (extractQueuedTempProductId(mutation) != null) {
    return true
  }
  return payloadHasUnresolvedTempProductId(mutation?.data) || payloadHasUnresolvedTempProductId(mutation?.params)
}

function toTimestamp(value) {
  if (!value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.getTime()
}

function normalizeQueuedMutations(rows) {
  const normalized = []
  const indexByPolicyAndKey = new Map()
  const supersededIds = []

  for (const row of rows || []) {
    const method = String(row?.method || '').toLowerCase()
    const policy = String(row?.conflictPolicy || inferConflictPolicy(row) || 'lww')
    const resourceKey = String(row?.resourceKey || inferResourceKey(row) || '')

    if (!resourceKey || (method !== 'post' && method !== 'put' && method !== 'delete')) {
      normalized.push(row)
      continue
    }

    if (policy === 'guarded') {
      normalized.push(row)
      continue
    }

    const mapKey = `${policy}:${resourceKey}`
    const existingIndex = indexByPolicyAndKey.get(mapKey)

    if (existingIndex === undefined) {
      indexByPolicyAndKey.set(mapKey, normalized.length)
      normalized.push(row)
      continue
    }

    const existing = normalized[existingIndex]

    if (policy === 'merge') {
      const merged = mergeMutations(existing, row)
      normalized[existingIndex] = merged
      if (existing?.id) supersededIds.push(existing.id)
      indexByPolicyAndKey.set(mapKey, existingIndex)
      continue
    }

    if (existing?.id) supersededIds.push(existing.id)
    normalized[existingIndex] = row
    indexByPolicyAndKey.set(mapKey, existingIndex)
  }

  return { rows: normalized, supersededIds }
}

function mergeMutations(older, newer) {
  const method = String(newer?.method || older?.method || '').toLowerCase()
  if (method !== 'put') return newer

  const olderData = older?.data || {}
  const newerData = newer?.data || {}

  if (String(newer?.resourceKey || '').includes('/api/v1/custom-fields/values/')) {
    const olderValues = olderData?.values && typeof olderData.values === 'object' ? olderData.values : {}
    const newerValues = newerData?.values && typeof newerData.values === 'object' ? newerData.values : {}
    return {
      ...newer,
      data: {
        ...olderData,
        ...newerData,
        values: {
          ...olderValues,
          ...newerValues,
        },
      },
    }
  }

  return {
    ...newer,
    data: {
      ...olderData,
      ...newerData,
    },
  }
}

function inferResourceKey(mutation) {
  return String(mutation?.url || '')
}

function inferConflictPolicy(mutation) {
  const method = String(mutation?.method || '').toLowerCase()
  const url = String(mutation?.url || '')

  if (method === 'post') return 'guarded'
  if (!url) return 'lww'
  if (url.includes('/api/v1/custom-fields/values/')) return 'merge'
  if (url.includes('/api/v1/settings/')) return 'guarded'
  return 'lww'
}
