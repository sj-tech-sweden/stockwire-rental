import { beforeEach, describe, expect, it } from 'vitest'

import { resolveAppLocale, resolveLoginLocale } from '../../src/i18n'

function setNavigatorLocale(locale) {
  Object.defineProperty(window.navigator, 'language', {
    value: locale,
    configurable: true,
  })
  Object.defineProperty(window.navigator, 'languages', {
    value: [locale],
    configurable: true,
  })
}

describe('locale resolution', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('uses user preference before browser and company defaults', () => {
    setNavigatorLocale('en-US')
    localStorage.setItem('sw_company_default_language', 'sv')
    localStorage.setItem('sw_user_locale_42', 'sv')

    expect(resolveAppLocale(42)).toBe('sv')
  })

  it('uses browser language before company default when no user preference exists', () => {
    setNavigatorLocale('en-US')
    localStorage.setItem('sw_company_default_language', 'sv')

    expect(resolveAppLocale(null)).toBe('en')
  })

  it('uses company default when browser language is unsupported', () => {
    setNavigatorLocale('de-DE')
    localStorage.setItem('sw_company_default_language', 'sv')

    expect(resolveAppLocale(null)).toBe('sv')
  })

  it('uses browser language before server default on login locale resolution', () => {
    setNavigatorLocale('en-US')

    expect(resolveLoginLocale('sv')).toBe('en')
  })
})
