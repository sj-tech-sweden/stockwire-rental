export function shouldSuppressDuplicateCameraScan({
  lastCode,
  lastAt,
  code,
  now,
  cooldownMs = 1800,
}) {
  if (!code) return false
  return code === lastCode && (now - lastAt) < cooldownMs
}
