#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required"
  exit 1
fi

REPO="${1:-jorblad/eventcore-unified}"
MILESTONE_TITLE="M1 - Unified Core MVP"

if ! gh api "repos/${REPO}" >/dev/null 2>&1; then
  echo "Repository ${REPO} not found or no access"
  exit 1
fi

MILESTONE_NUMBER=$(gh api "repos/${REPO}/milestones" --jq ".[] | select(.title==\"${MILESTONE_TITLE}\") | .number" || true)
if [[ -z "${MILESTONE_NUMBER}" ]]; then
  MILESTONE_NUMBER=$(gh api -X POST "repos/${REPO}/milestones" -f title="${MILESTONE_TITLE}" --jq '.number')
fi

create_issue() {
  local title="$1"
  local body="$2"
  gh issue create -R "${REPO}" --title "${title}" --body "${body}" --milestone "${MILESTONE_TITLE}" --label "milestone:1"
}

if ! gh label list -R "${REPO}" --json name --jq '.[].name' | grep -qx 'milestone:1'; then
  gh label create "milestone:1" -R "${REPO}" --color "1D76DB" --description "Milestone 1 scope"
fi

create_issue "Foundation: FastAPI service skeleton and Quasar shell" "Establish modular backend and frontend shell with containerized run path."
create_issue "Mobile scanning MVP for jobs and cases" "Implement scan-first mobile flow and case scan expansion (#105, #112)."
create_issue "Fix viewport and scrolling consistency" "Enforce layout overflow policy and verify small viewport behavior (#114)."
create_issue "Device job info panel with enriched context" "Expand job info shown on device details (#118)."
create_issue "Financial transaction domain baseline" "Create report-safe transaction schema and stats endpoints."
create_issue "Zone editing and bulk subzone management foundations" "Add initial API and UI routes for zone edit/bulk flows (#117)."
create_issue "Defect report edit and comments timeline foundations" "Add model/API foundations for editable defect reports and comments (#115)."

echo "Milestone 1 issues created in ${REPO}"
