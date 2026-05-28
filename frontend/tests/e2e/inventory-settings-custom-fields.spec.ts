import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Inventory + settings custom fields flow', () => {
  test('prefill categories, create categorized product, and manage custom fields', async ({ page }) => {
    await ensureLoggedIn(page)

    await page.goto(`${base}/inventory`)
    await page.waitForLoadState('networkidle', { timeout: 40_000 })
    await page.getByRole('tab', { name: 'Categories' }).click()
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/api/v1/inventory/categories/prefill') && res.ok(), { timeout: 20_000 }),
      page.getByRole('button', { name: 'Reset category defaults' }).click(),
    ])

    await page.getByRole('tab', { name: 'Products' }).click()
    const newProductButton = page.getByRole('button', { name: 'New product' }).first()
    await expect(newProductButton).toBeVisible({ timeout: 20_000 })
    await newProductButton.click()

    const productDialog = page
      .locator('.q-dialog')
      .filter({ has: page.getByText('New product', { exact: true }) })
      .first()
    await expect(productDialog).toBeVisible({ timeout: 20_000 })

    const sku = `E2E-${Date.now()}`
    await productDialog.getByLabel('SKU', { exact: true }).fill(sku)
    await productDialog.getByLabel('Name').fill('E2E Category Product')
    await productDialog.getByRole('combobox', { name: /^Category$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible({ timeout: 20_000 })
    const audioOption = page.getByRole('option', { name: 'Audio' }).first()
    await expect(audioOption).toBeVisible({ timeout: 20_000 })
    await audioOption.click()
    await expect(page.getByRole('listbox')).not.toBeVisible({ timeout: 20_000 })
    await productDialog.getByLabel('Daily rate').fill('123.45')
    await productDialog.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText('Product created')).toBeVisible({ timeout: 20_000 })
    await page.keyboard.press('Escape')

    const createdRow = page.getByRole('row').filter({ hasText: sku }).first()
    await expect(createdRow).toBeVisible()
    await expect(createdRow).toContainText(/audio/i)

    await page.goto(`${base}/settings`)
    await page.waitForLoadState('networkidle', { timeout: 40_000 })
    await expect(page.getByText('Admin Settings')).toBeVisible()
    await page.getByRole('tab', { name: 'Custom Fields' }).click()

    await page.getByRole('button', { name: 'New field' }).click()
    const fieldDialog = page.getByRole('dialog')
    await expect(fieldDialog).toBeVisible()
    await fieldDialog.getByRole('combobox', { name: /^Entity type$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible({ timeout: 20_000 })
    await page.getByRole('option', { name: 'Products' }).click()
    await expect(page.getByRole('listbox')).not.toBeVisible({ timeout: 20_000 })
    await fieldDialog.getByLabel('Label').fill('Calibration date')
    await fieldDialog.getByLabel('Key').fill('calibration_date')
    await fieldDialog.getByRole('combobox', { name: /^Value type$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible({ timeout: 20_000 })
    await page.getByRole('option', { name: 'Date' }).click()
    await expect(page.getByRole('listbox')).not.toBeVisible({ timeout: 20_000 })
    await fieldDialog.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('Calibration date')).toBeVisible({ timeout: 20_000 })
  })
})
