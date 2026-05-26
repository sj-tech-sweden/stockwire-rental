function trimTrailingSlash(value) {
  return String(value || '').replace(/\/$/, '')
}

export function getRuntimeConfig() {
  return window.__APP_CONFIG__ || {}
}

export function getApiBaseUrl() {
  const runtimeConfig = getRuntimeConfig()
  const runtimeValue = trimTrailingSlash(runtimeConfig.API_BASE_URL || runtimeConfig.apiBaseUrl)
  if (runtimeValue) return runtimeValue

  const viteValue = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL)
  if (viteValue) return viteValue

  return trimTrailingSlash(window.location.origin)
}
