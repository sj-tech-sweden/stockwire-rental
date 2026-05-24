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
  const email = FIXED_EMAIL
  const password = FIXED_PASSWORD

  await page.goto(`${base}/setup`)

  const createAdminBtn = page.getByRole('button', { name: 'Create admin account' })
  const goToLoginBtn = page.getByRole('button', { name: 'Go to login' })
  const signInHeading = page.getByText('Sign in to continue')

  // The "First-time Setup" heading is always present on SetupPage regardless of
  // setup state, so we cannot use it to detect readiness. Instead wait for the
  // conditional action buttons that only render after onMounted's async
  // checkBootstrap() call resolves.
  await expect(createAdminBtn.or(goToLoginBtn)).toBeVisible({ timeout: 10_000 })

  if (await createAdminBtn.isVisible()) {
    await page.getByLabel('Full name').fill('E2E Admin')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await createAdminBtn.click()
    // authStore.setup() calls _setSession() which auto-logs the user in;
    // router.push('/') navigates directly to the dashboard — no login page appears.
    await expect(createAdminBtn).not.toBeVisible({ timeout: 15_000 })
  } else {
    // Setup already done: navigate to login and sign in with known credentials.
    await goToLoginBtn.click()
    await expect(signInHeading).toBeVisible({ timeout: 10_000 })
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(signInHeading).not.toBeVisible({ timeout: 15_000 })
  }

  await expect(page.getByText('Stockwire Rental')).toBeVisible({ timeout: 15_000 })
  return { email, password }
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
