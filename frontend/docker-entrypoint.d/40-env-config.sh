#!/usr/bin/env sh
set -eu

runtime_api_base_url="${API_BASE_URL:-${VITE_API_BASE_URL:-}}"
line_separator_char="$(printf '\342\200\250')"
paragraph_separator_char="$(printf '\342\200\251')"
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
  }' | sed "s/${line_separator_char}/\\\\u2028/g; s/${paragraph_separator_char}/\\\\u2029/g"
)"

cat > /usr/share/nginx/html/env-config.js <<EOF
window.__APP_CONFIG__ = Object.assign(
  {
    API_BASE_URL: "${escaped_runtime_api_base_url}",
  },
  window.__APP_CONFIG__ || {}
)
EOF
