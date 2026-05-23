import { expect, type Page, type APIRequestContext, test } from '@playwright/test'

export const base = process.env.E2E_BASE_URL || 'http://localhost:9000'
export const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000'

export type SessionInfo = {
  email: string
  password: string
}

export async function ensureLoggedIn(page: Page): Promise<SessionInfo> {
  const fullName = 'E2E Admin'
  let email = `e2e+admin+${Date.now()}@example.com`
  let password = 'P@ssw0rd123!'

  await page.goto(`${base}/setup`)

  const setupHeading = page.getByText('First-time Setup')
  const signInHeading = page.getByText('Sign in to continue')

  // Wait for the page to fully render before deciding which branch to take
  await expect(setupHeading.or(signInHeading)).toBeVisible({ timeout: 10_000 })

  if (await setupHeading.isVisible()) {
    await page.getByLabel('Full name').fill(fullName)
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await page.getByRole('button', { name: 'Create admin account' }).click()
    // Wait for the API call to complete before checking next state
    await expect(setupHeading).not.toBeVisible({ timeout: 15_000 })
  } else {
    const envEmail = process.env.E2E_ADMIN_EMAIL
    const envPassword = process.env.E2E_ADMIN_PASSWORD
    if (!envEmail || !envPassword) {
      test.skip(true, 'Setup is complete; set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run e2e suites.')
    }
    email = envEmail || email
    password = envPassword || password
    if (await page.getByRole('button', { name: 'Go to login' }).isVisible()) {
      await page.getByRole('button', { name: 'Go to login' }).click()
    }
  }

  if (await signInHeading.isVisible()) {
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    // Wait for navigation away from login page before returning
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
