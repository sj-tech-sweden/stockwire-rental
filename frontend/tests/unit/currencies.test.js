import { describe, expect, it } from 'vitest'

import {
  CURRENCY_OPTIONS,
  currencyOptionFor,
  filterCurrencyOptions,
  normalizeCurrencyCode,
} from '../../src/constants/currencies'

describe('currency helpers', () => {
  it('normalizes currency codes and applies fallback', () => {
    expect(normalizeCurrencyCode('sek')).toBe('SEK')
    expect(normalizeCurrencyCode(' eur ')).toBe('EUR')
    expect(normalizeCurrencyCode('')).toBe('SEK')
    expect(normalizeCurrencyCode('abcd', 'USD')).toBe('USD')
  })

  it('returns known option labels and creates fallback option for unknown valid code', () => {
    expect(currencyOptionFor('sek')).toEqual({ value: 'SEK', label: 'SEK - Swedish Krona' })
    expect(currencyOptionFor('xbt')).toEqual({ value: 'XBT', label: 'XBT' })
  })

  it('filters options by label or value', () => {
    const all = filterCurrencyOptions(CURRENCY_OPTIONS, '')
    expect(all.length).toBe(CURRENCY_OPTIONS.length)

    const byCode = filterCurrencyOptions(CURRENCY_OPTIONS, 'eur')
    expect(byCode.some(option => option.value === 'EUR')).toBe(true)

    const byLabel = filterCurrencyOptions(CURRENCY_OPTIONS, 'krona')
    expect(byLabel.some(option => option.value === 'SEK')).toBe(true)
  })
})
