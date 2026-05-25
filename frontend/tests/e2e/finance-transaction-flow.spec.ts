import { expect, test, type Locator, type Page } from '@playwright/test'

import { apiPost, base, ensureLoggedIn, getAccessToken } from './helpers/session'

async function openDialogSelect(page: Page, dialog: Locator, namePattern: RegExp) {
  const combobox = dialog.getByRole('combobox', { name: namePattern })
  const listbox = page.getByRole('listbox')

  for (const open of [
    async () => {
      await combobox.focus()
      await combobox.press('ArrowDown')
    },
    async () => {
      await combobox.evaluate(node => {
        const field = node.closest('.q-field')
        if (!field) return
        for (const type of ['mousedown', 'mouseup', 'click']) {
          field.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }))
        }
      })
    },
  ]) {
    await open()
    try {
      await expect(listbox).toBeVisible({ timeout: 3_000 })
      return listbox
    } catch {
      // Try the next open strategy.
    }
  }

  await expect(listbox).toBeVisible({ timeout: 20_000 })
  return listbox
}

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

  const jobsLoaded = page.waitForResponse(response => {
    return response.ok()
      && response.request().method() === 'GET'
      && /\/api\/v1\/jobs(?:\?|$)/.test(response.url())
  }, { timeout: 20_000 })
  await page.goto(`${base}/finance`)
  await page.waitForLoadState('networkidle', { timeout: 40_000 })
  await jobsLoaded
  await page.getByRole('button', { name: /new transaction/i }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByLabel(/amount/i).fill('125.50')
  const listbox = await openDialogSelect(page, dialog, /^Job$/i)
  await expect(listbox).toBeVisible({ timeout: 20_000 })
  await page.getByRole('option', { name: new RegExp(String(job.job_code), 'i') }).click()
  await expect(listbox).not.toBeVisible({ timeout: 20_000 })
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
