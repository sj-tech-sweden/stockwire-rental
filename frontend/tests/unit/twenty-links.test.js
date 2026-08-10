import { describe, expect, it } from 'vitest'

import { getTwentyCustomerUrl, getTwentyJobUrl, getTwentyRecordUrl } from '../../src/utils/twenty-links'

describe('twenty links', () => {
  it('builds record urls for supported Twenty entities', () => {
    expect(getTwentyRecordUrl('companies', 'cmp_123', 'https://api.twenty.com')).toBe('https://app.twenty.com/object/company/cmp_123')
    expect(getTwentyRecordUrl('opportunities', 'opp 123', 'https://api.twenty.com')).toBe('https://app.twenty.com/object/opportunity/opp%20123')
  })

  it('uses configured base urls and ignores unsupported inputs', () => {
    expect(getTwentyRecordUrl('companies', 'cmp_123', 'https://twenty.example.com/api')).toBe('https://twenty.example.com/object/company/cmp_123')
    expect(getTwentyRecordUrl('people', 'person_1', 'https://api.twenty.com')).toBeNull()
    expect(getTwentyRecordUrl('companies', '', 'https://api.twenty.com')).toBeNull()
  })

  it('only returns customer and job links for Twenty-synced records', () => {
    expect(getTwentyCustomerUrl({ external_source: 'twenty', external_reference: 'company_1' }, { base_url: 'https://api.twenty.com' })).toBe('https://app.twenty.com/object/company/company_1')
    expect(getTwentyCustomerUrl({ external_source: 'other', external_reference: 'company_1' }, { base_url: 'https://api.twenty.com' })).toBeNull()
    expect(getTwentyJobUrl({ external_source: 'Twenty', external_reference: 'opp_1' }, { base_url: 'https://api.twenty.com' })).toBe('https://app.twenty.com/object/opportunity/opp_1')
    expect(getTwentyJobUrl({ external_source: 'twenty', external_reference: null }, { base_url: 'https://api.twenty.com' })).toBeNull()
  })
})
