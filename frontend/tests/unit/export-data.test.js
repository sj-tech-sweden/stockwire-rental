import { describe, expect, it } from 'vitest'

import { collectExportColumns, serializeRowsToCsv, serializeRowsToJson } from '../../src/utils/export-data'

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
      { value: '-42' },
      { value: '-1.5e3' },
      { value: '-SUM(A1:A2)' },
    ])
    expect(csv).toBe("value\n'=2+2\n'+SUM(A1:A2)\n'@cmd\n-42\n-1.5e3\n'-SUM(A1:A2)\n")
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
