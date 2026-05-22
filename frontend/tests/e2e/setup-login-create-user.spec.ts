import { expect, test } from '@playwright/test'

const base = process.env.E2E_BASE_URL || 'http://localhost:9000'

async function ensureLoggedIn(page) {
  const fullName = 'E2E Admin'
  let email = `e2e+admin+${Date.now()}@example.com`
  let password = 'P@ssw0rd123!'

  await page.goto(`${base}/#/setup`)

  if (await page.getByText('First-time Setup').count()) {
    await page.getByLabel('Full name').fill(fullName)
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(password)
    await page.getByLabel('Confirm password').fill(password)
    await page.getByRole('button', { name: 'Create admin account' }).click()
  } else {
    const envEmail = process.env.E2E_ADMIN_EMAIL
    const envPassword = process.env.E2E_ADMIN_PASSWORD
    if (!envEmail || !envPassword) {
      test.skip(true, 'Setup is already complete; set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')
    }
    email = envEmail || email
    password = envPassword || password
    if (await page.getByRole('button', { name: 'Go to login' }).count()) {
      await page.getByRole('button', { name: 'Go to login' }).click()
    }
  }

  if (await page.getByText('Sign in to continue').count()) {
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
  }

  await expect(page.getByText('Stockwire Rental')).toBeVisible()
}

test.describe('Core module route smoke', () => {
  test('can load all main authenticated routes', async ({ page }) => {
    await ensureLoggedIn(page)

    const routes = [
      '/#/',
      '/#/inventory',
      '/#/jobs',
      '/#/customers',
      '/#/venues',
      '/#/finance',
      '/#/settings',
      '/#/activity',
      '/#/labels',
      '/#/scan',
      '/#/profile',
      '/#/users',
    ]

    for (const path of routes) {
      await page.goto(`${base}${path}`)
      await expect(page).not.toHaveURL(/#\/login/)
      await expect(page.locator('.q-page').first()).toBeVisible()
    }
  })
})
