import { expect, test } from '@playwright/test'

import { apiPost, base, ensureLoggedIn, getAccessToken } from './helpers/session'

test('labels template create and apply to selected entities', async ({ page, request }) => {
  const session = await ensureLoggedIn(page)
  const token = await getAccessToken(request, session)

  const now = Date.now()
  const product = await apiPost(request, token, '/api/v1/inventory/products', {
    sku: `LBL-${now}`,
    name: `Label Product ${now}`,
    category: 'audio',
    daily_rate: '15.00',
  })

  await page.goto(`${base}/labels`)

  await page.getByRole('combobox', { name: /^Entity$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible()
  await page.getByRole('option', { name: /^Products$/i }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible()

  await page.getByRole('combobox', { name: /^Select one or many$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible()
  await page.getByRole('option', { name: new RegExp(String(product.name), 'i') }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible()

  const templateName = `E2E Label Template ${now}`
  await page.getByLabel('Template name').fill(templateName)
  await page.getByRole('button', { name: /^Save$/i }).click()

  await page.getByRole('button', { name: /^New$/i }).click()
  await page.getByRole('combobox', { name: /^Template$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible()
  await page.getByRole('option', { name: new RegExp(templateName, 'i') }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible()

  await expect(page.getByLabel('Template name')).toHaveValue(templateName)

  const printButton = page.getByRole('button', { name: /^Print$/i })
  await expect(printButton).toBeEnabled()
})
