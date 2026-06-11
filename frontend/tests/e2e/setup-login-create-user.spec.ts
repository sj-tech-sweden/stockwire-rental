import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Core module route smoke', () => {
  test('can load all main authenticated routes', async ({ page }) => {
    // The route loop visits 12 paths. Quasar's orbit-sync async boot plugin
    // dynamically imports @orbit/* modules and performs IndexedDB operations
    // AFTER the page 'load' event, so Quasar doesn't mount (and <q-page> won't
    // appear) until those operations complete. Firefox is significantly slower
    // than Chromium at processing dynamic import chains from the dev server.
    // Use waitForLoadState('networkidle') per route so that all dynamic imports
    // and initial API calls complete before we assert on <q-page>.
    // Worst-case budget: ensureLoggedIn (~30 s) + 12 routes × 45 s each = ~570 s.
    test.setTimeout(600_000)

    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))

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
      errors.length = 0
      await page.goto(`${base}${path}`)
      await page.waitForLoadState('networkidle', { timeout: 40_000 })
      if (errors.length) {
        console.log(`[page errors on ${path}]`, errors.join('; '))
      }
      await expect(page).not.toHaveURL(/\/login/)
      await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible({ timeout: 15_000 })
    }
  })
})
