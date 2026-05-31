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

function toDate(value) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function computeInclusiveDays(startDate, endDate) {
  if (!startDate || !endDate) return null
  const oneDay = 24 * 60 * 60 * 1000
  const startUtc = Date.UTC(startDate.getFullYear(), startDate.getMonth(), startDate.getDate())
  const endUtc = Date.UTC(endDate.getFullYear(), endDate.getMonth(), endDate.getDate())
  const diffDays = Math.floor((endUtc - startUtc) / oneDay)
  if (diffDays < 0) return null
  return diffDays + 1
}

export function isRentalProduct(product) {
  return Boolean(product?.is_rental_product) || String(product?.product_type || '').toLowerCase() === 'rental'
}

export function countCategoryOverview(categories, categoryTree) {
  const hasTreeShape = Array.isArray(categoryTree) && categoryTree.some(node => Array.isArray(node?.children))
  const treeCount = hasTreeShape ? countTreeNodes(categoryTree) : 0
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
  const parseUsageHours = (value) => {
    if (value == null) return null
    if (typeof value === 'string' && value.trim() === '') return null
    const usageHours = Number(value)
    if (!Number.isFinite(usageHours)) return null
    return usageHours
  }

  let selected = null
  let selectedHours = Number.NEGATIVE_INFINITY
  for (const device of devices || []) {
    const usageHours = parseUsageHours(device?.usage_hours)
    if (usageHours == null) continue
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

export function findMostUsedProductByUsageDays(products, requirements, jobs) {
  const jobsById = new Map((jobs || []).map(job => [String(job?.id), job]))
  const productsById = new Map((products || []).map(product => [String(product?.id), product]))
  const totals = new Map()
  const reservingStatuses = new Set(['confirmed', 'in_progress'])

  for (const requirement of requirements || []) {
    const productId = requirement?.product_id ?? requirement?.productId
    if (productId == null) continue
    const product = productsById.get(String(productId))
    if (!product || isRentalProduct(product)) continue

    const quantity = Number(requirement?.quantity_required ?? requirement?.quantity ?? requirement?.qty ?? 0)
    if (!Number.isFinite(quantity) || quantity <= 0) continue

    const jobId = requirement?.job_id ?? requirement?.jobId
    const job = jobsById.get(String(jobId))
    if (!job) continue
    if (!reservingStatuses.has(String(job?.status || '').toLowerCase())) continue

    const startDate = toDate(job?.start_date ?? job?.startDate)
    const endDate = toDate(job?.end_date ?? job?.endDate ?? job?.start_date ?? job?.startDate)
    const days = computeInclusiveDays(startDate, endDate)
    if (!Number.isFinite(days) || days <= 0) continue

    const key = String(productId)
    const total = totals.get(key) || 0
    totals.set(key, total + (days * quantity))
  }

  let selectedProductId = null
  let selectedUsageDays = Number.NEGATIVE_INFINITY
  for (const [productId, usageDays] of totals.entries()) {
    if (usageDays <= selectedUsageDays) continue
    selectedProductId = productId
    selectedUsageDays = usageDays
  }

  if (selectedProductId == null || !Number.isFinite(selectedUsageDays)) return null
  const selectedProduct = productsById.get(selectedProductId) || null
  return {
    product: selectedProduct,
    usage_days: Math.round(selectedUsageDays * 100) / 100,
  }
}
