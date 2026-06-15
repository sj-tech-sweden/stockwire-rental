import { api } from '../boot/axios'

let enabled = true
let flushTimer = null
let buffer = []

const FLUSH_INTERVAL = 60_000
const API_BASE = '/api/v1/metrics/frontend'

export function disableMetrics() {
  enabled = false
  if (flushTimer) {
    clearInterval(flushTimer)
    flushTimer = null
  }
}

function enqueue(type, payload) {
  if (!enabled) return
  buffer.push({ type, payload })
}

function flush() {
  if (!enabled || buffer.length === 0) return
  const batch = buffer.splice(0, buffer.length)
  for (const item of batch) {
    const url = `${API_BASE}/${item.type}`
    try {
      api.post(url, item.payload, { timeout: 5000 }).catch(() => {})
    } catch {
    }
  }
}

export function startMetricsFlush() {
  if (flushTimer) return
  flushTimer = setInterval(flush, FLUSH_INTERVAL)
  window.addEventListener('beforeunload', flush)
}

export function stopMetricsFlush() {
  if (flushTimer) {
    clearInterval(flushTimer)
    flushTimer = null
  }
  window.removeEventListener('beforeunload', flush)
}

export function trackPageView(path) {
  enqueue('page-view', { path })
}

export function trackApiTiming(method, endpoint, durationSeconds) {
  enqueue('api-timing', { method, endpoint, duration_seconds: durationSeconds })
}

export function trackError(type) {
  enqueue('error', { type })
}
