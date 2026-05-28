import { describe, expect, it } from 'vitest'
import { collectImportSourceKeys, convertDimensionValueToCm, getImportValueBySourceKey, parseImportRows, resolveImportEntityType } from '../../src/utils/import-data'

describe('import-data utilities', () => {
  it('parses composite products/devices json payloads into a single row list', () => {
    const rows = parseImportRows(
      JSON.stringify({
        products: [{ sku: 'P-1', dimensions: { height: '2m' } }],
        devices: [{ asset_tag: 'D-1' }],
      }),
      'import.json'
    )

    expect(rows).toHaveLength(2)
    expect(rows[0].__import_entity_type).toBe('product')
    expect(rows[1].__import_entity_type).toBe('device')
  })

  it('parses csv files and preserves dot-path headers for nested mappings', () => {
    const rows = parseImportRows('entity_type,sku,dimensions.height\nproduct,P-1,1.5m\n', 'import.csv')

    expect(rows).toEqual([{ entity_type: 'product', sku: 'P-1', 'dimensions.height': '1.5m' }])
  })

  it('returns csv parse errors for non-json unknown-extension files', () => {
    expect(() => parseImportRows('not,json\n', 'import.txt')).toThrow('CSV must contain a header row and at least one data row')
  })

  it('collects nested source keys and supports nested value lookups', () => {
    const rows = [{ sku: 'P-1', dimensions: { height: '1.2m', width: '25cm' } }]
    const keys = collectImportSourceKeys(rows).sort()

    expect(keys).toEqual(['dimensions', 'dimensions.height', 'dimensions.width', 'sku'])
    expect(getImportValueBySourceKey(rows[0], 'dimensions.height')).toBe('1.2m')
  })

  it('converts meter values to cm', () => {
    expect(convertDimensionValueToCm('1.5m')).toBe(150)
    expect(convertDimensionValueToCm('1.5', 'dimensions.height_m')).toBe(150)
    expect(convertDimensionValueToCm('35cm')).toBe(35)
  })

  it('resolves entity type from row fields with fallback', () => {
    expect(resolveImportEntityType({ entity_type: 'devices' })).toBe('device')
    expect(resolveImportEntityType({}, 'product')).toBe('product')
  })
})
