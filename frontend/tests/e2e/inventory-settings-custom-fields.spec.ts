import { expect, test } from '@playwright/test'

const base = process.env.E2E_BASE_URL || 'http://localhost:9000'

test.describe('Inventory + settings custom fields flow', () => {
  test('prefill categories, create categorized product, and manage custom fields', async ({ page }) => {
    let email = `e2e+admin+${Date.now()}@example.com`
    const fullName = 'E2E Admin'
    let password = 'P@ssw0rd123!'

    await page.goto(`${base}/#/setup`)

    if (await page.getByText('First-time Setup').count()) {
      await page.getByLabel('Full name').fill(fullName)
      await page.getByLabel('Email').fill(email)
      await page.getByLabel('Password', { exact: true }).fill(password)
      await page.getByLabel('Confirm password').fill(password)
      await page.getByRole('button', { name: 'Create admin account' }).click()
    } else {
      const envEmail = process.env.E2E_ADMIN_EMAIL
      const envPassword = process.env.E2E_ADMIN_PASSWORD
      if (!envEmail || !envPassword) {
        test.skip(true, 'Setup is already complete; set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')
      }
      email = envEmail || email
      password = envPassword || password
      if (await page.getByRole('button', { name: 'Go to login' }).count()) {
        await page.getByRole('button', { name: 'Go to login' }).click()
      }
    }

    if (await page.getByText('Sign in to continue').count()) {
      await page.getByLabel('Email').fill(email)
      await page.getByLabel('Password').fill(password)
      await page.getByRole('button', { name: 'Sign in' }).click()
    }

    await expect(page.getByText('Stockwire Rental')).toBeVisible()

    await page.goto(`${base}/#/inventory`)
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
    await page.getByRole('option', { name: 'Audio' }).first().click()
    await page.getByLabel('Daily rate').fill('123.45')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText('Product created')).toBeVisible()
    await page.keyboard.press('Escape')

    await expect(page.getByText(sku)).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Audio' })).toBeVisible()

    await page.goto(`${base}/#/settings`)
    await expect(page.getByText('Admin Settings')).toBeVisible()
    await page.getByRole('tab', { name: 'Custom Fields' }).click()

    await page.getByRole('button', { name: 'New field' }).click()
    await page.getByLabel('Entity type').click()
    await page.getByRole('option', { name: 'Products' }).click()
    await page.getByLabel('Label').fill('Calibration date')
    await page.getByLabel('Key').fill('calibration_date')
    await page.getByLabel('Value type').click()
    await page.getByRole('option', { name: 'Date' }).click()
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('Field created')).toBeVisible()

    await page.getByLabel('Entity').click()
    await page.getByRole('option', { name: new RegExp(sku) }).click()
    await page.getByLabel('Calibration date').fill('2026-05-20')
    await page.getByRole('button', { name: 'Save Values' }).click()
    await expect(page.getByText('Values saved')).toBeVisible()
  })
})
