import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getApiBaseUrl } from '../../src/utils/runtime-config'

describe('getApiBaseUrl', () => {
  beforeEach(() => {
    delete window.__APP_CONFIG__
    vi.unstubAllEnvs()
  })

  it('uses runtime config before Vite env and trims a trailing slash', () => {
    window.__APP_CONFIG__ = { API_BASE_URL: 'https://runtime.example.com/' }
    vi.stubEnv('VITE_API_BASE_URL', 'https://vite.example.com/')

    expect(getApiBaseUrl()).toBe('https://runtime.example.com')
  })

  it('uses Vite env when runtime config is missing', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://vite.example.com/')

    expect(getApiBaseUrl()).toBe('https://vite.example.com')
  })

  it('falls back to window.location.origin when runtime and Vite values are missing', () => {
    expect(getApiBaseUrl()).toBe(window.location.origin)
  })
})
