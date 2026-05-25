import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Inventory + settings custom fields flow', () => {
  test('prefill categories, create categorized product, and manage custom fields', async ({ page }) => {
    await ensureLoggedIn(page)

    await page.goto(`${base}/inventory`)
    await page.getByRole('tab', { name: 'Categories' }).click()
    await page.getByRole('button', { name: 'Reset category defaults' }).click()
    await expect(page.getByText('Category prefill updated')).toBeVisible()
    await expect(page.getByText('Audio')).toBeVisible()

    await page.getByRole('tab', { name: 'Products' }).click()
    await page.getByRole('button', { name: 'New product' }).click()

    const productDialog = page.getByRole('dialog')
    await expect(productDialog).toBeVisible()

    const sku = `E2E-${Date.now()}`
    await productDialog.getByLabel('SKU', { exact: true }).fill(sku)
    await productDialog.getByLabel('Name').fill('E2E Category Product')
    await productDialog.getByRole('combobox', { name: /^Category$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Audio' }).first().click()
    await expect(page.getByRole('listbox')).not.toBeVisible()
    await productDialog.getByLabel('Daily rate').fill('123.45')
    await productDialog.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText('Product created')).toBeVisible()
    await page.keyboard.press('Escape')

    const createdRow = page.getByRole('row').filter({ hasText: sku }).first()
    await expect(createdRow).toBeVisible()
    await expect(createdRow).toContainText(/audio/i)

    await page.goto(`${base}/settings`)
    await expect(page.getByText('Admin Settings')).toBeVisible()
    await page.getByRole('tab', { name: 'Custom Fields' }).click()

    await page.getByRole('button', { name: 'New field' }).click()
    const fieldDialog = page.getByRole('dialog')
    await expect(fieldDialog).toBeVisible()
    await fieldDialog.getByRole('combobox', { name: /^Entity type$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Products' }).click()
    await expect(page.getByRole('listbox')).not.toBeVisible()
    await fieldDialog.getByLabel('Label').fill('Calibration date')
    await fieldDialog.getByLabel('Key').fill('calibration_date')
    await fieldDialog.getByRole('combobox', { name: /^Value type$/i }).click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Date' }).click()
    await expect(page.getByRole('listbox')).not.toBeVisible()
    await fieldDialog.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('Calibration date')).toBeVisible()
  })
})
