import { describe, expect, it } from 'vitest'
import {
  countCategoryOverview,
  countPendingMaintenance,
  findMostUsedDevice,
  findMostUsedProductByUsageDays,
  isRentalProduct
} from '../../src/utils/inventory-overview'

describe('inventory overview utilities', () => {
  it('detects rental products from flags and type', () => {
    expect(isRentalProduct({ is_rental_product: true })).toBe(true)
    expect(isRentalProduct({ product_type: 'rental' })).toBe(true)
    expect(isRentalProduct({ product_type: 'equipment' })).toBe(false)
  })

  it('counts categories from tree when present', () => {
    const count = countCategoryOverview([], [
      { id: 1, children: [{ id: 2, children: [] }] },
      { id: 3, children: [] },
    ])
    expect(count).toBe(3)
  })

  it('falls back to deduped flat categories when tree is a non-hierarchical fallback list', () => {
    const categories = [
      { id: 5, name: 'Audio' },
      { id: 5, name: 'Audio duplicate' },
      { name: 'Lighting' },
      { name: 'lighting' },
    ]
    expect(countCategoryOverview(categories, categories)).toBe(2)
  })

  it('deduplicates flat category list when tree is unavailable', () => {
    const count = countCategoryOverview([
      { id: 5, name: 'Audio' },
      { id: 5, name: 'Audio' },
      { name: 'Lighting' },
      { name: 'lighting' },
    ], [])
    expect(count).toBe(2)
  })

  it('counts scheduled and in-progress maintenance as pending', () => {
    const count = countPendingMaintenance([
      { status: 'scheduled' },
      { status: 'in_progress' },
      { status: 'completed' },
    ])
    expect(count).toBe(2)
  })

  it('selects device with highest usage hours', () => {
    const device = findMostUsedDevice([
      { asset_tag: 'DEV-1', usage_hours: 10 },
      { asset_tag: 'DEV-2', usage_hours: 12.4 },
      { asset_tag: 'DEV-3', usage_hours: 12.2 },
    ])

    expect(device).toEqual({ asset_tag: 'DEV-2', usage_hours: 12.4 })
  })

  it('returns a zero-hour device when it is the only measured usage', () => {
    const device = findMostUsedDevice([
      { asset_tag: 'DEV-0', usage_hours: 0 },
    ])

    expect(device).toEqual({ asset_tag: 'DEV-0', usage_hours: 0 })
  })

  it('returns no device when usage values are missing', () => {
    const device = findMostUsedDevice([
      { asset_tag: 'DEV-1', usage_hours: null },
      { asset_tag: 'DEV-2', usage_hours: '' },
    ])

    expect(device).toBeNull()
  })

  it('selects product with highest usage days weighted by quantity', () => {
    const usage = findMostUsedProductByUsageDays(
      [
        { id: 1, name: 'Camera kit' },
        { id: 2, name: 'Light stand' },
      ],
      [
        { product_id: 1, job_id: 10, quantity_required: 2 },
        { product_id: 1, job_id: 11, quantity_required: 1 },
        { product_id: 2, job_id: 10, quantity_required: 1 },
      ],
      [
        { id: 10, status: 'confirmed', start_date: '2026-01-01', end_date: '2026-01-03' },
        { id: 11, status: 'in_progress', start_date: '2026-01-05', end_date: '2026-01-05' },
      ]
    )

    expect(usage).toEqual({
      product: { id: 1, name: 'Camera kit' },
      usage_days: 7,
    })
  })

  it('ignores draft and cancelled jobs in usage-days totals', () => {
    const usage = findMostUsedProductByUsageDays(
      [
        { id: 1, name: 'Camera kit' },
        { id: 2, name: 'Light stand' },
      ],
      [
        { product_id: 1, job_id: 20, quantity_required: 10 },
        { product_id: 1, job_id: 22, quantity_required: 10 },
        { product_id: 2, job_id: 21, quantity_required: 1 },
      ],
      [
        { id: 20, status: 'draft', start_date: '2026-01-01', end_date: '2026-01-03' },
        { id: 21, status: 'confirmed', start_date: '2026-01-01', end_date: '2026-01-01' },
        { id: 22, status: 'cancelled', start_date: '2026-01-01', end_date: '2026-01-03' },
      ]
    )

    expect(usage).toEqual({
      product: { id: 2, name: 'Light stand' },
      usage_days: 1,
    })
  })
})
