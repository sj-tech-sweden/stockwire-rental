#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-jorblad/stockwire-rental}"
MILESTONE_TITLE="${2:-M1 - Stockwire Rental MVP}"

required_labels=(
  "priority:p0:FF4D4F:Critical priority"
  "priority:p1:F7B84B:High priority"
  "area:backend:1D76DB:Backend domain"
  "area:frontend:5319E7:Frontend domain"
  "area:infra:0E8A16:Infrastructure and CI"
)

for item in "${required_labels[@]}"; do
  IFS=':' read -r prefix suffix color desc <<<"${item}"
  label="${prefix}:${suffix}"
  if ! gh label list -R "${REPO}" --json name --jq '.[].name' | grep -qx "${label}"; then
    gh label create "${label}" -R "${REPO}" --color "${color}" --description "${desc}"
  fi
done

issue_data=$(gh issue list -R "${REPO}" --state open --limit 100 --json number,title,milestone)

for issue_num in $(echo "${issue_data}" | jq -r --arg m "${MILESTONE_TITLE}" '.[] | select(.milestone != null and .milestone.title == $m) | .number'); do
  title=$(echo "${issue_data}" | jq -r --argjson n "$issue_num" '.[] | select(.number == $n) | .title')
  labels=("priority:p1")

  case "${title}" in
    *"Foundation"*|*"Financial transaction"* )
      labels+=("priority:p0" "area:backend" "area:infra")
      ;;
    *"Mobile"*|*"viewport"*|*"Device job info"*)
      labels+=("area:frontend" "area:backend")
      ;;
    *"Zone"*|*"Defect"*)
      labels+=("area:backend" "area:frontend")
      ;;
    *)
      labels+=("area:backend")
      ;;
  esac

  gh issue edit "${issue_num}" -R "${REPO}" --add-label "$(IFS=,; echo "${labels[*]}")" >/dev/null
  echo "Labeled issue #${issue_num}: ${title}"
done

printf "Labels ensured and assigned for milestone '%s' in %s\n" "${MILESTONE_TITLE}" "${REPO}"
