function normalizedPart(value) {
  const text = String(value || '').trim()
  return text || ''
}

export function locationQueryFromParts(parts = {}) {
  const { name, address, city, postal_code, country } = parts
  return [name, address, city, postal_code, country].map(normalizedPart).filter(Boolean).join(', ')
}

export function googleMapsSearchUrl(locationQuery) {
  const query = normalizedPart(locationQuery)
  if (!query) return ''
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
}

export function googleMapsEmbedUrl(locationQuery) {
  const query = normalizedPart(locationQuery)
  if (!query) return ''
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`
}
