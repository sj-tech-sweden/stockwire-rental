import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Core module route smoke', () => {
  test('can load all main authenticated routes', async ({ page }) => {
    await ensureLoggedIn(page)

    const routes = [
      '/',
      '/inventory',
      '/jobs',
      '/customers',
      '/venues',
      '/finance',
      '/settings',
      '/activity',
      '/labels',
      '/scan',
      '/profile',
      '/users',
    ]

    for (const path of routes) {
      await page.goto(`${base}${path}`)
      await expect(page).not.toHaveURL(/\/login/)
      await expect(page.locator('.q-page').first()).toBeVisible()
    }
  })
})
