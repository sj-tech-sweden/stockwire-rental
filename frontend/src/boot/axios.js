import axios from 'axios'
import { Notify } from 'quasar'
import { getApiBaseUrl } from '../utils/runtime-config'
import { useAuthStore } from '../stores/auth'

const apiBaseUrl = getApiBaseUrl()

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000
})

let interceptorInstalled = false
let isRefreshing = false
let refreshPromise = null
let proactiveRefreshTimer = null

const REFRESH_BUFFER_SECONDS = 60

function isAuthError(error) {
  // 401/403 from an auth endpoint means the refresh token itself is rejected.
  return error?.response?.status === 401 || error?.response?.status === 403
}

function clearSession() {
  localStorage.removeItem('sw_token')
  localStorage.removeItem('sw_user')
  localStorage.removeItem('sw_refresh_token')
  delete api.defaults.headers.common['Authorization']
}

function redirectToLogin() {
  if (window.location.pathname === '/login') return
  const currentPath = window.location.pathname + window.location.search
  const target = `/login?reason=expired&redirect=${encodeURIComponent(currentPath)}`
  window.location.assign(target)
}

function isOnLoginPage() {
  return window.location.pathname === '/login'
}

function shouldHandleUnauthorized(error) {
  const status = error?.response?.status
  if (status !== 401) return false
  const url = String(error?.config?.url || '')
  // Never auto-refresh on auth endpoints — a 401 here means invalid credentials / expired state,
  // not a stale access token that can be refreshed.
  if (url.startsWith('/api/v1/auth/')) return false
  return true
}

function decodeJwtPayload(token) {
  if (!token) return null
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = atob(base64)
    return JSON.parse(json)
  } catch {
    return null
  }
}

function getAccessTokenExpiry(token) {
  const payload = decodeJwtPayload(token)
  if (!payload || !payload.exp) return null
  return payload.exp * 1000
}

function msUntilExpiry(expiryMs) {
  if (!expiryMs) return null
  return expiryMs - Date.now()
}

function scheduleProactiveRefresh() {
  if (proactiveRefreshTimer) {
    clearTimeout(proactiveRefreshTimer)
    proactiveRefreshTimer = null
  }

  const token = localStorage.getItem('sw_token')
  const refreshToken = localStorage.getItem('sw_refresh_token')
  if (!token || !refreshToken) return

  const expiryMs = getAccessTokenExpiry(token)
  const msLeft = msUntilExpiry(expiryMs)
  if (!msLeft) return

  // Refresh a short buffer before expiry so the access token is unlikely to
  // be rejected by the time the next request is made.
  const refreshIn = Math.max(1000, msLeft - REFRESH_BUFFER_SECONDS * 1000)
  proactiveRefreshTimer = setTimeout(() => {
    refreshAccessToken().catch(() => {
      // Failure is handled inside refreshAccessToken (logs out if unrecoverable).
    })
  }, refreshIn)
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('sw_refresh_token')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  // If a refresh is already in-flight, return that promise.
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true

  const headers = {
    'Content-Type': 'application/json',
    'X-Refresh-Token': refreshToken,
  }

  refreshPromise = axios.post(`${apiBaseUrl}/api/v1/auth/refresh`, {}, {
    withCredentials: true,
    headers
  }).then(({ data }) => {
    const newToken = data.access_token
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    localStorage.setItem('sw_token', newToken)
    if (data.user) {
      localStorage.setItem('sw_user', JSON.stringify(data.user))
    }
    if (data.refresh_token) {
      localStorage.setItem('sw_refresh_token', data.refresh_token)
    }
    scheduleProactiveRefresh()
    return newToken
  }).catch(refreshError => {
    // Only clear the session when the server explicitly rejects the refresh
    // token (401/403). Network errors or 5xx responses while the backend is
    // restarting/rebuilding are transient and should not log the user out.
    if (isAuthError(refreshError)) {
      clearSession()
      if (!isOnLoginPage()) {
        Notify.create({ type: 'warning', message: 'Your session expired. Please sign in again.', timeout: 3500 })
        redirectToLogin()
      }
    }
    throw refreshError
  }).finally(() => {
    isRefreshing = false
    refreshPromise = null
  })

  return refreshPromise
}

function installUnauthorizedInterceptor() {
  if (interceptorInstalled) return
  interceptorInstalled = true

  api.interceptors.response.use(
    response => response,
    async (error) => {
      if (!shouldHandleUnauthorized(error)) {
        return Promise.reject(error)
      }

      const originalRequest = error.config

      // If this request was already retried after a refresh and still gets a
      // 401, the refresh token is no longer valid.
      if (originalRequest._retry) {
        clearSession()
        if (!isOnLoginPage()) {
          Notify.create({
            type: 'negative',
            message: 'Session expired. Please sign in again.',
            timeout: 5000,
          })
          redirectToLogin()
        }
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        const newToken = await refreshAccessToken()
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }
  )
}

function setupProactiveRefresh() {
  if (typeof window === 'undefined') return

  // Refresh on startup if the token is already expired or about to expire.
  const token = localStorage.getItem('sw_token')
  if (token) {
    const expiryMs = getAccessTokenExpiry(token)
    const msLeft = msUntilExpiry(expiryMs)
    if (msLeft === null || msLeft <= REFRESH_BUFFER_SECONDS * 1000) {
      refreshAccessToken().catch(() => {})
    } else {
      scheduleProactiveRefresh()
    }
  }

  // When the app comes back into focus (e.g. mobile resume, tab switch), make
  // sure the access token is still valid and refresh proactively if needed.
  const onVisible = () => {
    if (document.visibilityState !== 'visible') return
    const t = localStorage.getItem('sw_token')
    const rt = localStorage.getItem('sw_refresh_token')
    if (!t || !rt) return
    const expiryMs = getAccessTokenExpiry(t)
    const msLeft = msUntilExpiry(expiryMs)
    if (msLeft === null || msLeft <= REFRESH_BUFFER_SECONDS * 1000) {
      refreshAccessToken().catch(() => {})
    }
  }
  document.addEventListener('visibilitychange', onVisible)
}

export default ({ app }) => {
  installUnauthorizedInterceptor()
  setupProactiveRefresh()
  app.config.globalProperties.$api = api
}
