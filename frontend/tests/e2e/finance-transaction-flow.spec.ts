import { expect, test } from '@playwright/test'

import { apiPost, base, ensureLoggedIn, getAccessToken } from './helpers/session'

test('finance transaction create/edit/settle flow', async ({ page, request }) => {
  const session = await ensureLoggedIn(page)
  const token = await getAccessToken(request, session)

  const now = Date.now()
  const customer = await apiPost(request, token, '/api/v1/customers', {
    name: `E2E Customer ${now}`,
    email: `finance-customer-${now}@example.com`,
  })

  const venue = await apiPost(request, token, '/api/v1/venues', {
    name: `E2E Venue ${now}`,
    city: 'Berlin',
  })

  const job = await apiPost(request, token, '/api/v1/jobs', {
    job_code: `FIN-${now}`,
    title: `Finance Flow ${now}`,
    customer_id: customer.id,
    venue_id: venue.id,
  })

  await page.goto(`${base}/#/finance`)
  await page.getByRole('button', { name: /new transaction/i }).click()

  await page.getByLabel(/^Job$/i).click()
  await page.getByRole('option', { name: new RegExp(String(job.job_code), 'i') }).click()
  await page.getByLabel(/description/i).fill(`Initial e2e transaction ${now}`)
  await page.getByLabel(/amount/i).fill('125.50')
  await page.getByRole('button', { name: /^Save$/i }).click()

  const row = page.locator('tbody tr').filter({ hasText: String(job.job_code) }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText('125.50')

  await row.locator('button').nth(1).click()
  await page.getByLabel(/amount/i).fill('245.75')
  await page.getByLabel(/description/i).fill(`Edited e2e transaction ${now}`)
  await page.getByRole('button', { name: /^Save$/i }).click()

  await expect(row).toContainText('245.75')
  await row.locator('button').first().click()

  const settledRow = page.locator('tbody tr').filter({ hasText: String(job.job_code) }).first()
  await expect(settledRow).toContainText(/settled|completed|paid/i)
})
