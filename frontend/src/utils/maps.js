function normalizedPart(value) {
  const text = String(value || '').trim()
  return text || ''
}

export function locationQueryFromParts(parts = {}) {
  const { name, address, city, postal_code, country, latitude, longitude } = parts
  if (latitude != null && longitude != null && String(latitude).trim() !== '' && String(longitude).trim() !== '') {
    return `${latitude},${longitude}`
  }
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

export function osmEmbedUrl(points = []) {
  const coords = points.filter(p => p && p.latitude != null && p.longitude != null)
  if (!coords.length) return ''
  const lats = coords.map(p => Number(p.latitude))
  const lons = coords.map(p => Number(p.longitude))
  const pad = 0.02
  const bbox = [
    Math.min(...lons) - pad,
    Math.min(...lats) - pad,
    Math.max(...lons) + pad,
    Math.max(...lats) + pad,
  ].join(',')
  const markers = coords.map(p => `&marker=${p.latitude},${p.longitude}`).join('')
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik${markers}`
}
