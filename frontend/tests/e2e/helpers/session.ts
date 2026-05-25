import { expect, type Page, type APIRequestContext } from '@playwright/test'

export const base = process.env.E2E_BASE_URL || 'http://localhost:9000'
export const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000'

export type SessionInfo = {
  email: string
  password: string
}

// Fixed credentials used across all sequential tests so that tests 2+ can reuse
// the account created by the first test without needing env vars.
const FIXED_EMAIL = process.env.E2E_ADMIN_EMAIL || 'e2e-admin@example.com'
const FIXED_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'P@ssw0rd123!'

export async function ensureLoggedIn(page: Page): Promise<SessionInfo> {
  const credentialCandidates: SessionInfo[] = [
    { email: FIXED_EMAIL, password: FIXED_PASSWORD },
    { email: 'admin@example.com', password: 'secret123' },
    { email: 'admin@stockwire.local', password: 'secret123' },
  ]

  // Avoid UI race conditions by resolving first-time setup via backend API first.
  const bootstrapRes = await page.request.get(`${apiBase}/api/v1/auth/bootstrap-status`)
  expect(bootstrapRes.ok()).toBeTruthy()
  const bootstrapPayload = await bootstrapRes.json()
  let selected = credentialCandidates[0]

  if (bootstrapPayload?.setup_needed) {
    const setupRes = await page.request.post(`${apiBase}/api/v1/auth/setup`, {
      data: { full_name: 'E2E Admin', email: selected.email, password: selected.password },
    })
    // Another parallel test/process may complete setup between calls.
    expect([201, 409]).toContain(setupRes.status())
  }

  let canLogin = false
  for (const candidate of credentialCandidates) {
    const loginProbe = await page.request.post(`${apiBase}/api/v1/auth/login`, {
      data: { email: candidate.email, password: candidate.password },
    })
    if (loginProbe.ok()) {
      selected = candidate
      canLogin = true
      break
    }
  }
  expect(canLogin).toBeTruthy()

  await page.goto(`${base}/login`)
  const signInHeading = page.getByText('Sign in to continue')
  await expect(signInHeading).toBeVisible({ timeout: 20_000 })

  await page.getByLabel('Email').fill(selected.email)
  await page.getByLabel('Password').fill(selected.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(signInHeading).not.toBeVisible({ timeout: 20_000 })

  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 })
  await expect(page.locator('.q-page').first()).toBeVisible({ timeout: 20_000 })
  return selected
}

export async function getAccessToken(request: APIRequestContext, session: SessionInfo): Promise<string> {
  const res = await request.post(`${apiBase}/api/v1/auth/login`, {
    data: { email: session.email, password: session.password },
  })
  expect(res.ok()).toBeTruthy()
  const payload = await res.json()
  return String(payload?.access_token || '')
}

export async function apiPost(request: APIRequestContext, token: string, path: string, data: unknown) {
  const response = await request.post(`${apiBase}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function apiPut(request: APIRequestContext, token: string, path: string, data: unknown) {
  const response = await request.put(`${apiBase}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}
