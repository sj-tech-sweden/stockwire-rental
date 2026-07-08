export function isRentalProduct(product) {
  return Boolean(product?.is_rental_product) || String(product?.product_type || '').toLowerCase() === 'rental'
}

export function isVisibleRequirementRow(row) {
  return Number(row?.quantity_required || 0) > 0 || Number(row?.quantity_picked || 0) > 0
}

export function filterRequirementSourceProducts(products = [], { includeRentalProducts = false } = {}) {
  return products.filter(product => includeRentalProducts || !isRentalProduct(product))
}
