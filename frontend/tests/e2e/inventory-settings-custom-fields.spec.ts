import { expect, test } from '@playwright/test'

import { base, ensureLoggedIn } from './helpers/session'

test.describe('Inventory + settings custom fields flow', () => {
  test('prefill categories, create categorized product, and manage custom fields', async ({ page }) => {
    await ensureLoggedIn(page)

    await page.goto(`${base}/inventory`)
    await page.getByRole('tab', { name: 'Categories' }).click()
    await page.getByRole('button', { name: 'Prefill defaults' }).click()
    await expect(page.getByText('Category defaults added')).toBeVisible()
    await expect(page.getByText('Audio')).toBeVisible()

    await page.getByRole('tab', { name: 'Products' }).click()
    await page.getByRole('button', { name: 'New product' }).click()

    const sku = `E2E-${Date.now()}`
    await page.getByLabel('SKU').fill(sku)
    await page.getByLabel('Name').fill('E2E Category Product')
    await page.getByLabel('Category').click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Audio' }).first().click()
    await page.getByLabel('Daily rate').fill('123.45')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText('Product created')).toBeVisible()
    await page.keyboard.press('Escape')

    await expect(page.getByText(sku)).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Audio' })).toBeVisible()

    await page.goto(`${base}/settings`)
    await expect(page.getByText('Admin Settings')).toBeVisible()
    await page.getByRole('tab', { name: 'Custom Fields' }).click()

    await page.getByRole('button', { name: 'New field' }).click()
    await page.getByLabel('Entity type').click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Products' }).click()
    await page.getByLabel('Label').fill('Calibration date')
    await page.getByLabel('Key').fill('calibration_date')
    await page.getByLabel('Value type').click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: 'Date' }).click()
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('Field created')).toBeVisible()

    await page.getByLabel('Entity').click()
    await expect(page.getByRole('listbox')).toBeVisible()
    await page.getByRole('option', { name: new RegExp(sku) }).click()
    await page.getByLabel('Calibration date').fill('2026-05-20')
    await page.getByRole('button', { name: 'Save Values' }).click()
    await expect(page.getByText('Values saved')).toBeVisible()
  })
})
