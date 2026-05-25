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

  await apiPost(request, token, '/api/v1/inventory/scan/process', {
    scan_code: assetTag,
    action: 'job_out',
    job_code: job.job_code,
  })

  await apiPost(request, token, '/api/v1/inventory/scan/process', {
    scan_code: assetTag,
    action: 'job_in',
    job_code: job.job_code,
  })

  await page.goto(`${base}/scan`)
  await expect(page.getByLabel('Scan code')).toBeVisible()
  await expect(page.getByRole('button', { name: /^Outtake$/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Intake$/i })).toBeVisible()
})
