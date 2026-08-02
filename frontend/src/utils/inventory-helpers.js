/**
 * Shared utilities for inventory info dialogs.
 */

/**
 * Build a zone path string by walking up the parent chain.
 * @param {number|null} zoneId
 * @param {Array} zones - All zones from the store
 * @returns {string}
 */
export function buildZonePath(zoneId, zones) {
  if (!zoneId) return ''
  const zone = zones.find(z => z.id === zoneId)
  if (!zone) return ''
  const parts = []
  let current = zone
  while (current) {
    parts.unshift(current.name || '')
    current = zones.find(z => z.id === current.parent_id)
  }
  return parts.join(' / ')
}

/**
 * Get the effective location zone ID for a device.
 * Falls back to the case device's location if the device itself has none.
 * @param {Object} device
 * @param {Array} devices - All devices from the store
 * @returns {number|null}
 */
export function getEffectiveZoneId(device, devices) {
  if (device.location_zone_id) return device.location_zone_id
  if (device.case_device_id) {
    const caseDevice = devices.find(d => d.id === device.case_device_id)
    if (caseDevice?.location_zone_id) return caseDevice.location_zone_id
  }
  return null
}

/**
 * Format a number as currency.
 * @param {number|null|undefined} value
 * @param {string} currency - ISO currency code (default: SEK)
 * @returns {string}
 */
export function formatMoney(value, currency = 'SEK') {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '0.00'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}
