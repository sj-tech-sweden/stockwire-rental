export function shouldSuppressDuplicateCameraScan({
  lastCode,
  lastAt,
  code,
  now,
  cooldownMs = 1800,
}) {
  if (!code) return false
  if (!Number.isFinite(now)) return false
  if (!Number.isFinite(cooldownMs) || cooldownMs <= 0) return false
  if (!lastCode || !Number.isFinite(lastAt) || lastAt <= 0) return false
  const elapsedMs = now - lastAt
  if (elapsedMs < 0) return false
  return code === lastCode && elapsedMs < cooldownMs
}
