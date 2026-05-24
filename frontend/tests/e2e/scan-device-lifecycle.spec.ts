import { expect, test } from '@playwright/test'

import { apiPost, base, ensureLoggedIn, getAccessToken } from './helpers/session'

test('scan device lifecycle job out and in flow', async ({ page, request }) => {
  const session = await ensureLoggedIn(page)
  const token = await getAccessToken(request, session)

  const now = Date.now()
  const assetTag = `E2E-SCAN-${now}`

  const customer = await apiPost(request, token, '/api/v1/customers', {
    name: `Scan Customer ${now}`,
    email: `scan-customer-${now}@example.com`,
  })

  const venue = await apiPost(request, token, '/api/v1/venues', {
    name: `Scan Venue ${now}`,
    city: 'Stockholm',
  })

  const job = await apiPost(request, token, '/api/v1/jobs', {
    job_code: `SCAN-${now}`,
    customer_id: customer.id,
    venue_id: venue.id,
    status: 'confirmed',
    description: `Scan lifecycle ${now}`,
  })

  const product = await apiPost(request, token, '/api/v1/inventory/products', {
    sku: `SCAN-SKU-${now}`,
    name: `Scan Device Product ${now}`,
    category: 'lighting',
    daily_rate: '10.00',
  })

  await apiPost(request, token, `/api/v1/inventory/products/${product.id}/devices`, {
    quantity: 1,
    auto_generate: false,
    asset_tag: assetTag,
    status: 'available',
    condition: 'good',
  })

  await apiPost(request, token, '/api/v1/jobs/requirements', {
    job_id: job.id,
    product_id: product.id,
    quantity_required: 1,
    quantity_picked: 0,
  })

  await page.goto(`${base}/scan`)

  await page.getByRole('button', { name: /^Outtake$/i }).click()
  await page.getByRole('combobox', { name: /^Select Job$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible()
  await page.getByRole('option', { name: new RegExp(String(job.job_code), 'i') }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible()
  await page.getByLabel('Scan code').fill(assetTag)
  await page.getByRole('button', { name: /scan device|scan/i }).click()

  await expect(page.getByText(assetTag).first()).toBeVisible()

  await page.getByRole('button', { name: /^Intake$/i }).click()
  await page.getByRole('combobox', { name: /^Select job with checked-out devices$/i }).click()
  await expect(page.getByRole('listbox')).toBeVisible()
  await page.getByRole('option', { name: new RegExp(String(job.job_code), 'i') }).click()
  await expect(page.getByRole('listbox')).not.toBeVisible()
  await page.getByLabel('Scan code').fill(assetTag)
  await page.getByRole('button', { name: /^Scan$/i }).click()

  await expect(page.getByText('No devices are currently checked out')).toBeVisible()
})
