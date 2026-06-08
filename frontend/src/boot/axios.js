import axios from 'axios'
import { Notify } from 'quasar'
import { getApiBaseUrl } from '../utils/runtime-config'
import { useAuthStore } from '../stores/auth'

const apiBaseUrl = getApiBaseUrl()

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000
})

let interceptorInstalled = false
let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

function clearSession() {
  localStorage.removeItem('sw_token')
  localStorage.removeItem('sw_user')
  sessionStorage.removeItem('sw_refresh_token')
  delete api.defaults.headers.common['Authorization']
}

function redirectToLogin() {
  const currentPath = window.location.pathname + window.location.search
  if (window.location.pathname === '/login') return
  const target = `/login?reason=expired&redirect=${encodeURIComponent(currentPath)}`
  window.location.assign(target)
}

function shouldHandleUnauthorized(error) {
  const status = error?.response?.status
  if (status !== 401) return false
  const url = String(error?.config?.url || '')
  if (url.includes('/api/v1/auth/login') || url.includes('/api/v1/auth/setup') || url.includes('/api/v1/auth/refresh')) return false
  return true
}

let refreshPromise = null

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

      if (originalRequest._retry) {
        clearSession()
        redirectToLogin()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        try {
          const token = await refreshPromise
          originalRequest.headers['Authorization'] = `Bearer ${token}`
          return api(originalRequest)
        } catch (err) {
          return Promise.reject(err)
        }
      }

      originalRequest._retry = true
      isRefreshing = true

      const headers = { 'Content-Type': 'application/json' }
      const store = useAuthStore()
      const storedRefreshToken = store.getRefreshToken()
      if (storedRefreshToken) {
        headers['X-Refresh-Token'] = storedRefreshToken
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
          sessionStorage.setItem('sw_refresh_token', data.refresh_token)
        }
        return newToken
      }).catch(refreshError => {
        clearSession()
        Notify.create({
          type: 'warning',
          message: 'Your session expired. Please sign in again.',
          timeout: 3500,
        })
        redirectToLogin()
        throw refreshError
      }).finally(() => {
        isRefreshing = false
        refreshPromise = null
      })

      try {
        const newToken = await refreshPromise
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }
  )
}

export default ({ app }) => {
  installUnauthorizedInterceptor()
  app.config.globalProperties.$api = api
}
