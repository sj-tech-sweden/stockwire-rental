/**
 * Screenshot capture script for PR documentation.
 *
 * Captures full-page screenshots of affected pages in dark mode.
 *
 * Prerequisites: The dev stack must be running.
 *   npm run screenshots:up
 *
 * Usage:
 *   # All pages (local dev)
 *   npx playwright test tests/e2e/screenshots.spec.ts --project=chromium
 *
 *   # Specific pages
 *   SCREENSHOT_PAGES=crew,companies,jobs npx playwright test tests/e2e/screenshots.spec.ts --project=chromium
 *
 *   # CI: auto-detects from git diff (set CI=true)
 */
import { execSync } from 'child_process'
import { test, expect } from '@playwright/test'

import { base, apiBase, ensureLoggedIn } from './helpers/session'

const SCREENSHOT_DIR = 'tests/e2e/artifacts/screenshots'

// Map of route paths to file patterns that affect them
const routePatterns: Record<string, string[]> = {
  '/': ['app/main.py', 'app/domain/auth/', 'frontend/src/App.vue', 'frontend/src/layouts/'],
  '/jobs': ['app/domain/jobs/', 'frontend/src/pages/Job', 'frontend/src/pages/JobsPage'],
  '/customers': ['app/domain/customers/', 'frontend/src/pages/Company', 'frontend/src/pages/CompaniesPage', 'frontend/src/pages/CustomerDetail'],
  '/inventory': ['app/domain/inventory/', 'frontend/src/pages/Inventory', 'frontend/src/components/Product', 'frontend/src/components/RentalProduct'],
  '/crew': ['app/domain/crew/', 'frontend/src/pages/Crew', 'frontend/src/components/Crew', 'frontend/src/components/SkillAutocomplete', 'frontend/src/components/MyCertifications'],
  '/finance': ['app/domain/finance/', 'frontend/src/pages/Finance', 'frontend/src/components/Transaction'],
  '/venues': ['app/domain/venues/', 'frontend/src/pages/Venue'],
  '/settings': ['app/domain/settings/', 'frontend/src/pages/Settings'],
  '/labels': ['app/domain/labels/', 'frontend/src/pages/Label', 'frontend/src/components/Label'],
  '/scan': ['app/domain/scan/', 'frontend/src/pages/Scan', 'frontend/src/components/Scan'],
  '/activity': ['app/domain/activity/', 'frontend/src/pages/Activity'],
}

const allPages = [
  { path: '/', name: 'dashboard' },
  { path: '/jobs', name: 'jobs' },
  { path: '/customers', name: 'companies' },
  { path: '/inventory', name: 'inventory' },
  { path: '/crew', name: 'crew' },
  { path: '/finance', name: 'finance' },
  { path: '/venues', name: 'venues' },
  { path: '/settings', name: 'settings' },
  { path: '/labels', name: 'labels' },
  { path: '/scan', name: 'scan' },
  { path: '/activity', name: 'activity' },
]

function getChangedFiles(): string[] {
  try {
    const baseRef = process.env.GITHUB_BASE_REF || 'origin/main'
    const output = execSync(`git diff --name-only ${baseRef}...HEAD 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || echo ""`, {
      encoding: 'utf-8',
      cwd: process.env.GITHUB_WORKSPACE || process.cwd(),
    })
    return output.trim().split('\n').filter(Boolean)
  } catch {
    return []
  }
}

function getAffectedPages(changedFiles: string[]): typeof allPages {
  if (!changedFiles.length) return allPages

  const affected = new Set<string>()
  for (const file of changedFiles) {
    for (const [route, patterns] of Object.entries(routePatterns)) {
      if (patterns.some(p => file.startsWith(p) || file.includes(p))) {
        affected.add(route)
      }
    }
  }

  if (affected.size === 0) return allPages
  affected.add('/')
  return allPages.filter(p => affected.has(p.path))
}

function resolvePages(): typeof allPages {
  const envPages = process.env.SCREENSHOT_PAGES
  if (envPages) {
    const names = envPages.split(',').map(s => s.trim().toLowerCase())
    return allPages.filter(p => names.includes(p.name))
  }

  if (process.env.CI === 'true') {
    const changed = getChangedFiles()
    console.log(`[screenshots] Changed files: ${changed.join(', ') || '(none detected)'}`)
    const pages = getAffectedPages(changed)
    console.log(`[screenshots] Capturing ${pages.length} affected page(s): ${pages.map(p => p.name).join(', ')}`)
    return pages
  }

  return allPages
}

async function applyDarkMode(page: import('@playwright/test').Page) {
  // Emulate dark color scheme at the browser level
  await page.emulateMedia({ colorScheme: 'dark' })
  // Tell Quasar to enable dark mode via its API
  await page.evaluate(() => {
    // @ts-expect-error Quasar global
    if (window.__QUASAR_SSR__ !== undefined || window.Quasar?.Dark) {
      // @ts-expect-error Quasar global
      window.Quasar?.Dark?.set(true)
    }
    // Fallback: set the localStorage value Quasar reads on boot
    try { localStorage.setItem('q Dark', 'true') } catch { /* ignore */ }
  })
}

test.describe('PR screenshots', () => {
  test('capture affected pages', async ({ page }) => {
    test.setTimeout(300_000)

    // Check that services are reachable before attempting login
    let backendUp = false
    try {
      const res = await page.request.get(`${apiBase}/api/v1/auth/bootstrap-status`)
      backendUp = res.ok()
      if (backendUp) {
        const body = await res.json()
        console.log(`[screenshots] Backend status: setup_needed=${body.setup_needed}`)
      }
    } catch {
      backendUp = false
    }

    if (!backendUp) {
      console.error(`
╔══════════════════════════════════════════════════════════════╗
║  Backend is not reachable at ${apiBase}             ║
║                                                              ║
║  Start the dev stack first:                                  ║
║    npm run screenshots:up                                    ║
║  or                                                          ║
║    docker compose -f ../infra/compose/docker-compose.dev.yml up -d --build
╚══════════════════════════════════════════════════════════════╝
`)
      expect(backendUp, 'Backend must be running. See message above.').toBeTruthy()
    }

    const pagesToCapture = resolvePages()
    if (!pagesToCapture.length) {
      console.log('[screenshots] No pages to capture')
      return
    }

    await ensureLoggedIn(page)

    // Apply dark mode before capturing
    await applyDarkMode(page)

    for (const { path, name } of pagesToCapture) {
      await page.goto(`${base}${path}`, { waitUntil: 'networkidle', timeout: 45_000 })
      await applyDarkMode(page)
      await page.waitForTimeout(500)
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/${name}-dark.png`,
        fullPage: true,
      })
      console.log(`[screenshots] Captured: ${name}-dark.png`)
    }

    console.log(`[screenshots] Done! ${pagesToCapture.length} screenshot(s) saved to ${SCREENSHOT_DIR}/`)
  })
})
