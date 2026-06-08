import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sw_token') || null)
  const me = ref(JSON.parse(localStorage.getItem('sw_user') || 'null'))
  let _refreshToken = sessionStorage.getItem('sw_refresh_token') || null

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => me.value?.role === 'admin')
  const isManager = computed(() => me.value?.role === 'manager')
  const isViewer = computed(() => me.value?.role === 'viewer')
  const canManageSettings = computed(() => isAdmin.value)
  const canEdit = computed(() => isAdmin.value || isManager.value)

  // Restore Authorization header on page reload
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  function _storeRefreshToken(refreshToken) {
    _refreshToken = refreshToken
    if (refreshToken) {
      sessionStorage.setItem('sw_refresh_token', refreshToken)
    } else {
      sessionStorage.removeItem('sw_refresh_token')
    }
  }

  function _setSession(data) {
    token.value = data.access_token
    me.value = data.user
    localStorage.setItem('sw_token', data.access_token)
    localStorage.setItem('sw_user', JSON.stringify(data.user))
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    if (data.refresh_token) {
      _storeRefreshToken(data.refresh_token)
    }
  }

  function _setToken(accessToken) {
    token.value = accessToken
    localStorage.setItem('sw_token', accessToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
  }

  function _setUser(data) {
    if (data?.user) {
      me.value = data.user
      localStorage.setItem('sw_user', JSON.stringify(data.user))
    }
    if (data?.refresh_token) {
      _storeRefreshToken(data.refresh_token)
    }
  }

  function getRefreshToken() {
    return _refreshToken
  }

  function logout() {
    api.post('/api/v1/auth/logout').catch(() => {})
    token.value = null
    me.value = null
    _refreshToken = null
    localStorage.removeItem('sw_token')
    localStorage.removeItem('sw_user')
    sessionStorage.removeItem('sw_refresh_token')
    delete api.defaults.headers.common['Authorization']
  }

  async function login(email, password) {
    const { data } = await api.post('/api/v1/auth/login', { email, password })
    _setSession(data)
  }

  async function setup(email, password, fullName) {
    const { data } = await api.post('/api/v1/auth/setup', {
      email,
      password,
      full_name: fullName,
      role: 'admin',
    })
    _setSession(data)
  }

  // User list (admin-only)
  const users = ref([])
  const apiKeys = ref([])
  const ssoProviders = ref([])

  async function fetchUsers() {
    try {
      const { data } = await api.get('/api/v1/auth/users')
      users.value = data.users || data
      await cacheSnapshot('auth.users', users.value)
      return users.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('auth.users')
        if (Array.isArray(cached)) {
          users.value = cached
          return users.value
        }
      }
      throw error
    }
  }

  async function createUser(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      users.value = [...users.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/auth/users', data: payload, conflictPolicy: 'guarded' })
      return optimistic
    }
    const { data } = await api.post('/api/v1/auth/users', payload)
    users.value = [...users.value, data]
    return data
  }

  async function updateUser(id, payload) {
    if (!isOnline()) {
      users.value = users.value.map(u => u.id === id ? { ...u, ...payload, _offline_queued: true } : u)
      await queueMutation({ method: 'put', url: `/api/v1/auth/users/${id}`, data: payload, conflictPolicy: 'lww' })
      return users.value.find(u => u.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/auth/users/${id}`, payload)
    users.value = users.value.map(u => u.id === id ? data : u)
    return data
  }

  async function deleteUser(id) {
    if (!isOnline()) {
      users.value = users.value.filter(u => u.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/auth/users/${id}`, conflictPolicy: 'lww' })
      return
    }
    await api.delete(`/api/v1/auth/users/${id}`)
    users.value = users.value.filter(u => u.id !== id)
  }

  async function checkBootstrap() {
    const { data } = await api.get('/api/v1/auth/bootstrap-status')
    return data.setup_needed
  }

  async function fetchMe() {
    const { data } = await api.get('/api/v1/auth/me')
    me.value = data || null
    localStorage.setItem('sw_user', JSON.stringify(me.value))
    return me.value
  }

  async function updateMyProfile(payload) {
    const body = {
      email: String(payload?.email || '').trim(),
      full_name: String(payload?.full_name || '').trim(),
      password: String(payload?.password || '').trim() || null,
    }
    const { data } = await api.put('/api/v1/auth/me', body)
    me.value = data || null
    localStorage.setItem('sw_user', JSON.stringify(me.value))
    return me.value
  }

  async function fetchSsoProviders() {
    const { data } = await api.get('/api/v1/auth/sso/providers')
    ssoProviders.value = Array.isArray(data) ? data : []
    return ssoProviders.value
  }

  async function getOidcAuthorizeUrl(provider, redirectUri) {
    const { data } = await api.get(`/api/v1/auth/sso/oidc/authorize/${encodeURIComponent(provider)}`, {
      params: { redirect_uri: redirectUri },
    })
    return data?.authorize_url || ''
  }

  async function oidcExchange(provider, code, redirectUri) {
    const { data } = await api.post('/api/v1/auth/sso/oidc/exchange', {
      provider,
      code,
      redirect_uri: redirectUri,
    })
    _setSession(data)
  }

  async function samlLogin(provider, samlResponse) {
    const { data } = await api.post('/api/v1/auth/sso/saml/login', {
      provider,
      saml_response: samlResponse,
    })
    _setSession(data)
  }

  async function fetchApiKeys() {
    try {
      const { data } = await api.get('/api/v1/auth/api-keys')
      apiKeys.value = data
      await cacheSnapshot('auth.apiKeys', apiKeys.value)
      return apiKeys.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('auth.apiKeys')
        if (Array.isArray(cached)) {
          apiKeys.value = cached
          return apiKeys.value
        }
      }
      throw error
    }
  }

  async function createApiKey(payload) {
    if (!isOnline()) {
      const optimistic = {
        id: -Date.now(),
        name: payload?.name || 'offline-key',
        _offline_queued: true,
      }
      apiKeys.value = [...apiKeys.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/auth/api-keys', data: payload, conflictPolicy: 'guarded' })
      return optimistic
    }
    const { data } = await api.post('/api/v1/auth/api-keys', payload)
    apiKeys.value = [...apiKeys.value, data]
    return data
  }

  async function deleteApiKey(id) {
    if (!isOnline()) {
      apiKeys.value = apiKeys.value.filter(k => k.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/auth/api-keys/${id}`, conflictPolicy: 'lww' })
      return
    }
    await api.delete(`/api/v1/auth/api-keys/${id}`)
    apiKeys.value = apiKeys.value.filter(k => k.id !== id)
  }

  return {
    me,
    token,
    isAuthenticated,
    isAdmin,
    isManager,
    isViewer,
    canManageSettings,
    canEdit,
    _setToken,
    _setUser,
    getRefreshToken,
    login,
    setup,
    logout,
    checkBootstrap,
    fetchMe,
    updateMyProfile,
    ssoProviders,
    fetchSsoProviders,
    getOidcAuthorizeUrl,
    oidcExchange,
    samlLogin,
    users,
    fetchUsers,
    createUser,
    updateUser,
    deleteUser,
    apiKeys,
    fetchApiKeys,
    createApiKey,
    deleteApiKey,
  }
})
