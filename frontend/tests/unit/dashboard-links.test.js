import { describe, expect, it } from 'vitest'

import { dashboardJobRoute, dashboardProductRoute, dashboardScanRoute } from '../../src/utils/dashboard-links'

describe('dashboard links', () => {
  it('builds job and product routes only for valid ids', () => {
    expect(dashboardJobRoute(12)).toEqual({ path: '/jobs', query: { focusJobId: '12' } })
    expect(dashboardJobRoute(0)).toBeNull()
    expect(dashboardProductRoute(7)).toEqual({ path: '/inventory', query: { tab: 'products', focusProductId: '7' } })
    expect(dashboardProductRoute(null)).toBeNull()
  })

  it('maps scan activity rows to the right deep-link target', () => {
    expect(dashboardScanRoute({ job_id: 3, device_id: 9, product_id: 11, zone_id: 13 })).toEqual({
      path: '/jobs',
      query: { focusJobId: '3' },
    })
    expect(dashboardScanRoute({ device_id: 9 })).toEqual({
      path: '/inventory',
      query: { tab: 'devices', focusDeviceId: '9' },
    })
    expect(dashboardScanRoute({ product_id: 11 })).toEqual({
      path: '/inventory',
      query: { tab: 'products', focusProductId: '11' },
    })
    expect(dashboardScanRoute({ zone_id: 13 })).toEqual({
      path: '/inventory',
      query: { tab: 'locations', focusLocationId: '13' },
    })
    expect(dashboardScanRoute({})).toEqual({ path: '/activity' })
  })
})
