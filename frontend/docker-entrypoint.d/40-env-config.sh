#!/usr/bin/env sh
set -eu

runtime_api_base_url="${API_BASE_URL:-${VITE_API_BASE_URL:-}}"
escaped_runtime_api_base_url="$(
  printf '%s' "${runtime_api_base_url}" | awk 'BEGIN { first = 1 } {
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    gsub(/\r/, "\\r")
    if (!first) {
      printf "\\n"
    }
    printf "%s", $0
    first = 0
  }'
)"

cat > /usr/share/nginx/html/env-config.js <<EOF
window.__APP_CONFIG__ = Object.assign(
  {
    API_BASE_URL: "${escaped_runtime_api_base_url}",
  },
  window.__APP_CONFIG__ || {}
)
EOF
