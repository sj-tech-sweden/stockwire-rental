import { describe, it, expect } from 'vitest'
import { slugify } from '../../src/utils/slugify'

describe('slugify util', () => {
  it('replaces å ä ö and maps to ascii equivalents', () => {
    expect(slugify('Åland')).toBe('aland')
    expect(slugify('Småland')).toBe('smaland')
    expect(slugify('Fägring')).toBe('fagring')
    expect(slugify('KÖR')).toBe('kor')
  })

  it('removes punctuation and spaces', () => {
    expect(slugify('Hello, World!')).toBe('hello-world')
  })
})
