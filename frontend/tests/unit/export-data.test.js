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
        [10, { id: 10, name: 'LED Panel' }],
        [11, { id: 11, name: 'Should Not Replace' }],
      ]),
      zoneById: new Map([
        [20, { id: 20, name: 'Warehouse A', code: 'WH-A' }],
        [21, { id: 21, name: 'Warehouse B', code: 'WH-B' }],
      ]),
    })

    expect(rows).toEqual([
      { id: 1, product_id: 10, location_zone_id: 20, product_name: 'LED Panel', location_name: 'Warehouse A', location_code: 'WH-A' },
      { id: 2, product_id: 11, location_zone_id: 21, product_name: 'Existing Name', location_name: 'Warehouse B', location_code: 'EXIST' },
    ])
  })

  it('keeps non-device rows unchanged when enriching export rows', () => {
    const input = [{ id: 1, sku: 'P-1' }]
    expect(enrichInventoryExportRows('products', input)).toEqual(input)
  })
})
