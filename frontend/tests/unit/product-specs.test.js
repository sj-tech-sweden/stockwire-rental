import { describe, expect, it } from 'vitest'
import {
  calculateSpeakerThrow,
  PRODUCT_SPEC_GROUPS,
  PRODUCT_SPEC_FIELDS,
} from '../../src/utils/productSpecs.js'

describe('speaker product specifications', () => {
  it('exposes dispersion and calculated throw in the speaker group', () => {
    const speakerFields = PRODUCT_SPEC_GROUPS.find((group) => group.key === 'speaker').fields

    expect(speakerFields).toContain('dispersion_h_deg')
    expect(speakerFields).toContain('throw_m')
    expect(speakerFields).toContain('target_spl_db')
    expect(PRODUCT_SPEC_FIELDS.dispersion_h_deg.unit).toBe('°')
    expect(PRODUCT_SPEC_FIELDS.throw_m.unit).toBe('m')
  })

  it('calculates free-field throw from max SPL and target SPL', () => {
    expect(calculateSpeakerThrow(100, 94)).toBe(2)
    expect(calculateSpeakerThrow(100, 100)).toBe(1)
    expect(calculateSpeakerThrow(94, 100)).toBe(0.5)
  })

  it('does not calculate throw when either SPL value is missing or invalid', () => {
    expect(calculateSpeakerThrow(null, 94)).toBeNull()
    expect(calculateSpeakerThrow(100, null)).toBeNull()
    expect(calculateSpeakerThrow('not-a-number', 94)).toBeNull()
    expect(calculateSpeakerThrow(100, 'not-a-number')).toBeNull()
  })
})
