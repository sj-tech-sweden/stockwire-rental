import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Core module route smoke', () => {
  test('can load all main authenticated routes', async ({ page }) => {
    // The route loop visits 12 paths, some with lazy-loaded components (e.g.
    // /users) whose async chunk load can push Firefox past the default 30 s
    // test timeout. Give the test 2 minutes so every route has time to settle.
    test.setTimeout(120_000)

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
      // Use a longer timeout per route: Firefox may need extra time to finish
      // loading lazily-imported page chunks before <q-page> appears in the DOM.
      await expect(page.locator('.q-page').first()).toBeVisible({ timeout: 20_000 })
    }
  })
})
