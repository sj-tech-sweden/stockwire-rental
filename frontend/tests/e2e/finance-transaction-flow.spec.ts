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

  await page.goto(`${base}/finance`)
  await page.waitForLoadState('networkidle', { timeout: 40_000 })
  await page.getByRole('button', { name: /new transaction/i }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  // Fill a text field first so webkit fully establishes focus inside the dialog
  // before any q-select combobox interaction (avoids the webkit issue where a
  // combobox clicked as the very first dialog interaction never opens its portal).
  await dialog.getByLabel(/amount/i).fill('125.50')
  await dialog.getByRole('combobox', { name: /^Job$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('option', { name: new RegExp(String(job.job_code), 'i') }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible({ timeout: 20_000 })
  await dialog.getByRole('button', { name: /^Save$/i }).click()
  await expect(dialog).not.toBeVisible()

  const transactionsTable = page.locator('.q-table__container').last()
  const row = transactionsTable.locator('tbody tr').filter({ hasText: String(job.job_code) }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText(/125[.,]50/)

  await row.locator('button').nth(1).click()
  const editDialog = page.getByRole('dialog')
  await expect(editDialog).toBeVisible()
  await editDialog.getByLabel(/amount/i).fill('245.75')
  await editDialog.getByRole('button', { name: /^Save$/i }).click()
  await expect(editDialog).not.toBeVisible()

  await expect(row).toContainText(/245[.,]75/)
  await row.locator('button').first().click()

  const settledRow = transactionsTable.locator('tbody tr').filter({ hasText: String(job.job_code) }).first()
  await expect(settledRow).toContainText(/settled|completed|paid/i)
})
