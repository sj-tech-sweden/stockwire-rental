#!/usr/bin/env sh
set -eu

runtime_api_base_url="${API_BASE_URL:-${VITE_API_BASE_URL:-}}"

cat > /usr/share/nginx/html/env-config.js <<EOF
window.__APP_CONFIG__ = Object.assign(
  {
    API_BASE_URL: "${runtime_api_base_url}",
  },
  window.__APP_CONFIG__ || {}
)
EOF
