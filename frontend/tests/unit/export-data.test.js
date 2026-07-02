import { describe, expect, it } from 'vitest'

import { collectExportColumns, enrichInventoryExportRows, serializeRowsToCsv, serializeRowsToJson } from '../../src/utils/export-data'

describe('export-data utilities', () => {
  it('collects export columns in first-seen order across rows', () => {
    expect(collectExportColumns([
      { id: 1, name: 'A' },
      { name: 'B', status: 'active' },
    ])).toEqual(['id', 'name', 'status'])
  })

  it('serializes rows to CSV with escaping for commas, quotes, and line breaks', () => {
    const csv = serializeRowsToCsv([
      { id: 1, note: 'plain' },
      { id: 2, note: 'hello, "csv"\nnext' },
      { id: 3, note: 'carriage\rreturn' },
    ])
    expect(csv).toBe('id,note\n1,plain\n2,"hello, ""csv""\nnext"\n3,"carriage\rreturn"\n')
  })

  it('sanitizes spreadsheet formulas while keeping negative numbers intact', () => {
    const csv = serializeRowsToCsv([
      { value: '=2+2' },
      { value: '+SUM(A1:A2)' },
      { value: '@cmd' },
      { value: '\ttab-prefixed' },
      { value: '\rreturn-prefixed' },
      { value: '-42' },
      { value: '-1.5e3' },
      { value: '-SUM(A1:A2)' },
    ])
    expect(csv).toBe([
      'value',
      "'=2+2",
      "'+SUM(A1:A2)",
      "'@cmd",
      "'\ttab-prefixed",
      `"'\rreturn-prefixed"`,
      '-42',
      '-1.5e3',
      "'-SUM(A1:A2)",
      '',
    ].join('\n'))
  })

  it('serializes rows to pretty JSON and ignores invalid rows', () => {
    const json = serializeRowsToJson([
      { id: 1, tags: ['a', 'b'] },
      null,
      'nope',
    ])
    expect(JSON.parse(json)).toEqual([{ id: 1, tags: ['a', 'b'] }])
  })

  it('enriches device export rows with product and location display fields', () => {
    const rows = enrichInventoryExportRows('devices', [
      { id: 1, product_id: 10, location_zone_id: 20 },
      { id: 2, product_id: 11, location_zone_id: 21, product_name: 'Existing Name', location_code: 'EXIST' },
    ], {
      productById: new Map([
        [10, { id: 10, name: 'LED Panel', sku: 'LED-01', category: 'Lighting', brand: 'Ayrton', manufacturer: 'Ayrton Inc' }],
        [11, { id: 11, name: 'Should Not Replace', sku: 'SPK-01', category: 'Audio', brand: null, manufacturer: null }],
      ]),
      zoneById: new Map([
        [20, { id: 20, name: 'Warehouse A', code: 'WH-A' }],
        [21, { id: 21, name: 'Warehouse B', code: 'WH-B' }],
      ]),
    })

    expect(rows).toEqual([
      {
        id: 1, product_id: 10, location_zone_id: 20,
        product_name: 'LED Panel', product_sku: 'LED-01', product_category: 'Lighting',
        product_brand: 'Ayrton', product_manufacturer: 'Ayrton Inc',
        location_name: 'Warehouse A', location_code: 'WH-A',
      },
      {
        id: 2, product_id: 11, location_zone_id: 21,
        product_name: 'Existing Name', product_sku: 'SPK-01', product_category: 'Audio',
        product_brand: '', product_manufacturer: '',
        location_name: 'Warehouse B', location_code: 'EXIST',
      },
    ])
  })

  it('appends product custom fields with cf_ prefix when enriching device export rows', () => {
    const rows = enrichInventoryExportRows('devices', [
      { id: 1, product_id: 10, location_zone_id: 0 },
    ], {
      productById: new Map([
        [10, { id: 10, name: 'Cable XLR 5m', sku: 'CBL-001', category: 'Cables', brand: null, manufacturer: null }],
      ]),
      zoneById: new Map(),
      customFieldValuesByEntityId: new Map([
        [10, { cable_type: 'XLR', length_m: '5' }],
      ]),
    })

    expect(rows[0].cf_cable_type).toBe('XLR')
    expect(rows[0].cf_length_m).toBe('5')
  })

  it('appends product custom fields with cf_ prefix when enriching product export rows', () => {
    const rows = enrichInventoryExportRows('products', [
      { id: 1, sku: 'CBL-001', name: 'Cable XLR 5m' },
      { id: 2, sku: 'LED-01', name: 'LED Panel' },
    ], {
      customFieldValuesByEntityId: new Map([
        [1, { cable_type: 'XLR', length_m: '5' }],
        [2, {}],
      ]),
    })

    expect(rows[0]).toMatchObject({ id: 1, sku: 'CBL-001', cf_cable_type: 'XLR', cf_length_m: '5' })
    expect(rows[1]).toMatchObject({ id: 2, sku: 'LED-01' })
    expect(rows[1].cf_cable_type).toBeUndefined()
  })

  it('keeps non-device rows unchanged when enriching export rows without custom fields', () => {
    const input = [{ id: 1, sku: 'P-1' }]
    expect(enrichInventoryExportRows('products', input)).toEqual(input)
  })
})
