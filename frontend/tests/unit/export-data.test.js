import { describe, expect, it } from 'vitest'

import { collectExportColumns, serializeRowsToCsv, serializeRowsToJson } from '../../src/utils/export-data'

describe('export-data utilities', () => {
  it('collects export columns in first-seen order across rows', () => {
    expect(collectExportColumns([
      { id: 1, name: 'A' },
      { name: 'B', status: 'active' },
    ])).toEqual(['id', 'name', 'status'])
  })

  it('serializes rows to CSV with escaping for commas, quotes, and newlines', () => {
    const csv = serializeRowsToCsv([
      { id: 1, note: 'plain' },
      { id: 2, note: 'hello, "csv"\nnext' },
    ])
    expect(csv).toBe('id,note\n1,plain\n2,"hello, ""csv""\nnext"\n')
  })

  it('serializes rows to pretty JSON and ignores invalid rows', () => {
    const json = serializeRowsToJson([
      { id: 1, tags: ['a', 'b'] },
      null,
      'nope',
    ])
    expect(JSON.parse(json)).toEqual([{ id: 1, tags: ['a', 'b'] }])
  })
})
