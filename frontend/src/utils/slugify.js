export function slugify(input) {
  const s = String(input ?? '').trim()
  if (!s) return ''
  // Map Scandinavian letters to url-friendly letters
  const mapped = s
    .replace(/[ÅÄåä]/g, 'a')
    .replace(/[Öö]/g, 'o')
  return mapped
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

export default slugify
