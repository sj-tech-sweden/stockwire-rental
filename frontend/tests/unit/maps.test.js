import { describe, expect, it } from 'vitest'

import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../../src/utils/maps'

describe('maps helpers', () => {
  it('builds a location query from available venue parts', () => {
    expect(locationQueryFromParts({ name: 'Main Hall', address: 'Street 1', city: 'Stockholm' })).toBe('Main Hall, Street 1, Stockholm')
    expect(locationQueryFromParts({ name: 'Main Hall', city: 'Stockholm' })).toBe('Main Hall, Stockholm')
    expect(locationQueryFromParts({})).toBe('')
  })

  it('creates encoded Google Maps URLs', () => {
    const query = 'Main Hall, Street 1, Stockholm'
    expect(googleMapsSearchUrl(query)).toBe('https://www.google.com/maps/search/?api=1&query=Main%20Hall%2C%20Street%201%2C%20Stockholm')
    expect(googleMapsEmbedUrl(query)).toBe('https://www.google.com/maps?q=Main%20Hall%2C%20Street%201%2C%20Stockholm&output=embed')
    expect(googleMapsSearchUrl('')).toBe('')
    expect(googleMapsEmbedUrl('')).toBe('')
  })
})
