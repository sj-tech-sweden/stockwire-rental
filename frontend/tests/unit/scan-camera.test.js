import { describe, expect, it } from 'vitest'

import { shouldSuppressDuplicateCameraScan } from '../../src/utils/scan-camera'

describe('shouldSuppressDuplicateCameraScan', () => {
  it('suppresses the same code during cooldown window', () => {
    const suppressed = shouldSuppressDuplicateCameraScan({
      lastCode: 'DEV-001',
      lastAt: 1_000,
      code: 'DEV-001',
      now: 2_000,
      cooldownMs: 1_500,
    })

    expect(suppressed).toBe(true)
  })

  it('allows the same code after cooldown window', () => {
    const suppressed = shouldSuppressDuplicateCameraScan({
      lastCode: 'DEV-001',
      lastAt: 1_000,
      code: 'DEV-001',
      now: 2_600,
      cooldownMs: 1_500,
    })

    expect(suppressed).toBe(false)
  })

  it('allows different codes immediately', () => {
    const suppressed = shouldSuppressDuplicateCameraScan({
      lastCode: 'DEV-001',
      lastAt: 1_000,
      code: 'DEV-002',
      now: 1_100,
      cooldownMs: 1_500,
    })

    expect(suppressed).toBe(false)
  })

  it('allows scans when previous scan state is missing', () => {
    const suppressed = shouldSuppressDuplicateCameraScan({
      lastCode: '',
      lastAt: 0,
      code: 'DEV-002',
      now: 1_100,
      cooldownMs: 1_500,
    })

    expect(suppressed).toBe(false)
  })
})
