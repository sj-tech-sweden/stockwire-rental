import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test('finance transaction create/edit/settle flow', async ({ page }) => {
  await ensureLoggedIn(page)

  const now = Date.now()
  const initialAmount = Number((100 + ((now % 9000) / 100)).toFixed(2))
  const updatedAmount = Number((initialAmount + 120.25).toFixed(2))
  const moneyPattern = (value: number) => new RegExp(String(value.toFixed(2)).replace('.', '[.,]'))

  await page.goto(`${base}/finance`)
  await page.waitForLoadState('networkidle', { timeout: 40_000 })
  await page.getByRole('button', { name: /new transaction/i }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByLabel(/amount/i).fill(initialAmount.toFixed(2))

  const createResponsePromise = page.waitForResponse(
    (resp) => resp.url().includes('/api/v1/finance/transactions') && resp.request().method() === 'POST',
  )
  await dialog.getByRole('button', { name: /^Save$/i }).click()
  await expect(dialog).not.toBeVisible()
  const createResponse = await createResponsePromise
  expect(createResponse.ok()).toBeTruthy()
  const createResponseJson = (await createResponse.json()) as { id?: string | number }
  expect(createResponseJson.id).toBeDefined()
  const transactionId = String(createResponseJson.id)

  const transactionsTable = page.locator('.q-table__container').last()
  const getRowById = (id: string) =>
    transactionsTable
      .locator('tbody tr')
      .filter({
        has: transactionsTable.getByRole('cell', { name: id, exact: true }),
      })
      .first()

  const row = getRowById(transactionId)
  await expect(row).toBeVisible()
  await expect(row).toContainText(moneyPattern(initialAmount))

  await row.locator('button').nth(1).click()
  const editDialog = page.getByRole('dialog')
  await expect(editDialog).toBeVisible()
  await editDialog.getByLabel(/amount/i).fill(updatedAmount.toFixed(2))
  await editDialog.getByRole('button', { name: /^Save$/i }).click()
  await expect(editDialog).not.toBeVisible()

  const updatedRow = getRowById(transactionId)
  await expect(updatedRow).toContainText(moneyPattern(updatedAmount))
  await updatedRow.locator('button').first().click()

  const settledRow = getRowById(transactionId)
  await expect(settledRow).toContainText(/settled|completed|paid/i)
})
