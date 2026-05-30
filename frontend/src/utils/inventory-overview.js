function countTreeNodes(nodes) {
  let total = 0
  const walk = (items) => {
    for (const item of items || []) {
      total += 1
      walk(item.children || [])
    }
  }
  walk(nodes)
  return total
}

export function isRentalProduct(product) {
  return Boolean(product?.is_rental_product) || String(product?.product_type || '').toLowerCase() === 'rental'
}

export function countCategoryOverview(categories, categoryTree) {
  const treeCount = countTreeNodes(categoryTree)
  if (treeCount > 0) return treeCount

  const unique = new Set()
  for (const category of categories || []) {
    const id = Number(category?.id)
    if (Number.isFinite(id) && id > 0) {
      unique.add(`id:${id}`)
      continue
    }
    const name = String(category?.name || '').trim().toLowerCase()
    if (name) unique.add(`name:${name}`)
  }
  return unique.size
}

export function countPendingMaintenance(maintenances) {
  let pending = 0
  for (const row of maintenances || []) {
    const status = String(row?.status || '').toLowerCase()
    if (status === 'scheduled' || status === 'in_progress') pending += 1
  }
  return pending
}

export function findMostUsedDevice(devices) {
  let selected = null
  let selectedHours = Number.NEGATIVE_INFINITY
  for (const device of devices || []) {
    const usageHours = Number(device?.usage_hours)
    if (!Number.isFinite(usageHours)) continue
    if (selected && usageHours <= selectedHours) continue
    selected = device
    selectedHours = usageHours
  }
  if (!selected) return null
  return {
    asset_tag: selected.asset_tag || null,
    usage_hours: Math.round(selectedHours * 10) / 10,
  }
}
