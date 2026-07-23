# Product & Rental Category Filter Fix Plan

## Context

Two issues with category filtering:
1. **Products tab**: The category dropdown shows categories derived from `product.category` strings on ALL products (including rental products), which doesn't match the canonical category tree defined in Settings. It includes rental product categories and shows flat names instead of hierarchical paths.
2. **Rentals tab**: No category filter exists at all, despite `category` being a table column.

## Root Cause

- `productCategoryOptions` (line 1060) builds options from `store.products[].category` strings — includes rental products, doesn't use the category tree
- The filter compares `product.category` (string) instead of `product.category_id` (FK)
- `allCategorySelectOptions` (line 1380) already exists and correctly builds hierarchical options from `store.categoryTree` — but isn't used by the filter
- Rental products use free-text `category` strings (no `category_id`), so they need their own filter approach

## Changes

### 1. Products tab — use category tree for filter

**File: `frontend/src/pages/InventoryPage.vue`**

- Replace `productCategoryOptions` computed to use `store.categoryTree` (reuse existing `allCategorySelectOptions` which already does this)
- Change filter logic in `filteredProducts` to compare `product.category_id` against selected value (instead of `product.category` string)
- Handle `category_id` being null (products without a tree-linked category)

**Replace `productCategoryOptions` (lines 1060-1063):**
```js
const productCategoryOptions = computed(() => {
  const flat = []
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return flat
})
```

**Update filter in `filteredProducts` (line 942):**
```js
// Before:
if (productCategoryFilter.value && String(product.category || '') !== String(productCategoryFilter.value)) return false
// After:
if (productCategoryFilter.value && product.category_id !== productCategoryFilter.value) return false
```

### 2. Rentals tab — add category filter

**File: `frontend/src/pages/InventoryPage.vue`**

- Add `rentalProductCategoryFilter` ref (initialized to `null`)
- Add `rentalCategoryOptions` computed from unique `category` strings on rental products only
- Add `q-select` to the rentals filter bar template
- Apply filter in `filteredRentalProducts`

**New ref (near line 831):**
```js
const rentalProductCategoryFilter = ref(null)
```

**New computed (near `rentalSupplierOptions`):**
```js
const rentalCategoryOptions = computed(() => {
  const values = [...new Set(rentalProducts.value.map(item => String(item.category || '').trim()).filter(Boolean))]
  return values.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})
```

**Add to rentals filter bar template (after supplier dropdown, before sync dropdown):**
```html
<div class="col-12 col-sm-6 col-md-3">
  <q-select
    v-model="rentalProductCategoryFilter"
    :options="rentalCategoryOptions"
    :label="t('inventory.category')"
    outlined
    dense
    clearable
    emit-value
    map-options
  />
</div>
```

**Add filter to `filteredRentalProducts` (line ~1001):**
```js
if (rentalProductCategoryFilter.value && String(product.category || '') !== String(rentalProductCategoryFilter.value)) return false
```

### 3. i18n

No new keys needed — `inventory.category` already exists.

## Files Modified

1. `frontend/src/pages/InventoryPage.vue` — all changes in this single file

## Verification

1. Products tab: Category dropdown should show hierarchical tree paths (e.g. "Audio / Speakers") from Settings > Categories, not random strings from product data
2. Products tab: Selecting a category should filter to only inventory (non-rental) products with that `category_id`
3. Rentals tab: Category dropdown should show unique category strings from rental products only
4. Rentals tab: Selecting a category should filter rental products by that category string
5. Clearing filters: Both category filters should clear properly with the `clearable` prop
