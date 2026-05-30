import { describe, expect, it } from 'vitest'
import { countCategoryOverview, countPendingMaintenance, findMostUsedDevice, isRentalProduct } from '../../src/utils/inventory-overview'

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
      { asset_tag: 'DEV-2', usage_hours: 12.26 },
      { asset_tag: 'DEV-3', usage_hours: 12.2 },
    ])

    expect(device).toEqual({ asset_tag: 'DEV-2', usage_hours: 12.3 })
  })
})
