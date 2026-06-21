#!/usr/bin/env sh
set -eu

runtime_api_base_url="${API_BASE_URL:-${VITE_API_BASE_URL:-}}"
metrics_backend_origin="${METRICS_BACKEND_ORIGIN:-http://127.0.0.1:8000}"
# Normalize: ensure a scheme is present and strip any trailing slash
case "${metrics_backend_origin}" in
  http://*|https://*) ;;
  *) metrics_backend_origin="http://${metrics_backend_origin}" ;;
esac
metrics_backend_origin="${metrics_backend_origin%/}"
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
escaped_metrics_backend_origin="$(printf '%s' "${metrics_backend_origin}" | sed 's/\\/\\\\/g; s/[$`&|]/\\&/g')"

sed -i "s|__METRICS_BACKEND_ORIGIN__|${escaped_metrics_backend_origin}|g" /etc/nginx/conf.d/default.conf

cat > /usr/share/nginx/html/env-config.js <<EOF
window.__APP_CONFIG__ = Object.assign(
  {
    API_BASE_URL: "${escaped_runtime_api_base_url}",
  },
  window.__APP_CONFIG__ || {}
)
EOF
