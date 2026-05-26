import axios from 'axios'
import { Notify } from 'quasar'
import { getApiBaseUrl } from '../utils/runtime-config'

const apiBaseUrl = getApiBaseUrl()

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000
})

let interceptorInstalled = false
let handlingUnauthorized = false

function clearSession() {
  localStorage.removeItem('sw_token')
  localStorage.removeItem('sw_user')
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
  if (url.includes('/api/v1/auth/login') || url.includes('/api/v1/auth/setup')) return false
  return true
}

function installUnauthorizedInterceptor() {
  if (interceptorInstalled) return
  interceptorInstalled = true

  api.interceptors.response.use(
    response => response,
    (error) => {
      if (shouldHandleUnauthorized(error) && !handlingUnauthorized) {
        handlingUnauthorized = true
        clearSession()
        Notify.create({
          type: 'warning',
          message: 'Your session expired. Please sign in again.',
          timeout: 3500,
        })
        redirectToLogin()
      }
      return Promise.reject(error)
    }
  )
}

export default ({ app }) => {
  installUnauthorizedInterceptor()
  app.config.globalProperties.$api = api
}
