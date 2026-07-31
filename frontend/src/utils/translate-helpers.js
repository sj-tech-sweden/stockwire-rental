/**
 * Translation helpers for product types and categories.
 *
 * Product types are stored as English strings (equipment, accessory, etc.)
 * and need to be translated to the user's locale when displayed.
 *
 * Categories use a two-tier translation system:
 * 1. Database translations (from category_translations table) — highest priority
 * 2. Static prefill mapping (from prefillContent.js) — fallback for known English names
 * 3. Original name — fallback for unknown categories
 */

import { CATEGORY_SEGMENT_KEY_BY_CANONICAL } from '../i18n/prefillContent'

/**
 * Map of product type values to their i18n keys.
 */
const PRODUCT_TYPE_I18N_KEYS = {
  equipment: 'inventory.productTypeEquipment',
  accessory: 'inventory.productTypeAccessory',
  consumable: 'inventory.productTypeConsumable',
  case: 'inventory.productTypeCase',
  bundle: 'inventory.productTypeBundle',
  rental: 'inventory.productTypeRental',
  crew: 'inventory.productTypeCrew',
}

/**
 * Translate a product type value to its localized label.
 * @param {string|null} type - The raw product type value
 * @param {Function} t - The i18n translation function
 * @returns {string} The translated label, or the original value if no translation exists
 */
export function translateProductType(type, t) {
  if (!type) return '-'
  const key = PRODUCT_TYPE_I18N_KEYS[type]
  return key ? t(key) : type
}

/**
 * Translate a category name.
 * Uses DB translations first (if available), then static prefill mapping, then original name.
 * @param {string|null} category - The raw category name
 * @param {Function} t - The i18n translation function
 * @param {Map|null} dbTranslations - Map of {categoryName: translatedName} from DB
 * @returns {string} The translated name
 */
export function translateCategory(category, t, dbTranslations = null) {
  if (!category) return '-'

  // 1. Check DB translations
  if (dbTranslations) {
    const translated = dbTranslations.get(category)
    if (translated) return translated
  }

  // 2. Check static prefill mapping
  const normalized = category.trim().toLowerCase()
  const key = CATEGORY_SEGMENT_KEY_BY_CANONICAL[normalized]
  if (key) return t(key)

  // 3. Return original
  return category
}
