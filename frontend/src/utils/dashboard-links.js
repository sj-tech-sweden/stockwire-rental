export function dashboardJobRoute(jobId) {
  const targetId = Number(jobId || 0)
  if (!targetId) return null
  return { path: '/jobs', query: { focusJobId: String(targetId) } }
}

export function dashboardProductRoute(productId) {
  const targetId = Number(productId || 0)
  if (!targetId) return null
  return { path: '/inventory', query: { tab: 'products', focusProductId: String(targetId) } }
}

export function dashboardScanRoute(item) {
  const jobRoute = dashboardJobRoute(item?.job_id)
  if (jobRoute) return jobRoute

  const deviceId = Number(item?.device_id || 0)
  if (deviceId > 0) {
    return { path: '/inventory', query: { tab: 'devices', focusDeviceId: String(deviceId) } }
  }

  const productRoute = dashboardProductRoute(item?.product_id)
  if (productRoute) return productRoute

  const zoneId = Number(item?.zone_id || 0)
  if (zoneId > 0) {
    return { path: '/inventory', query: { tab: 'locations', focusLocationId: String(zoneId) } }
  }

  return { path: '/activity' }
}
