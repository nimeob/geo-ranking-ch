#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "MISSING_COMMAND:$cmd" >&2
    exit 2
  fi
}

require_cmd gh
require_cmd jq
require_cmd mktemp
require_cmd base64

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [[ -z "${TOKEN}" ]]; then
  TOKEN="$(./scripts/gh_app_token.sh)"
fi
if [[ -z "${TOKEN}" ]]; then
  echo "NO_TOKEN" >&2
  exit 2
fi

export GITHUB_TOKEN="$TOKEN"
export GH_TOKEN="$TOKEN"

REPO="nimeob/geo-ranking-ch"

tmp_json="$(mktemp)"
trap 'rm -f "$tmp_json"' EXIT

# get issues with zero labels
gh issue list --repo "$REPO" --state open --json number,title,labels -L 1000 >"$tmp_json"
mapfile -t issue_rows < <(jq -r '.[] | select((.labels|length)==0) | @base64' "$tmp_json")

if (( ${#issue_rows[@]} == 0 )); then
  echo "NO_ZERO_LABEL_ISSUES"
  exit 0
fi

labelled=()
checked=0

for row in "${issue_rows[@]}"; do
  [[ -z "$row" ]] && continue
  checked=$((checked+1))

  issue_json=$(printf '%s' "$row" | base64 --decode)
  num=$(jq -r '.number' <<<"$issue_json")
  title=$(jq -r '.title' <<<"$issue_json")
  title_lc=$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]')

  labels=(backlog "status:todo")

  # priority
  if [[ "$title" == *"P0"* || "$title_lc" == *"p0"* ]]; then labels+=("priority:P0");
  elif [[ "$title" == *"P1"* || "$title_lc" == *"p1"* ]]; then labels+=("priority:P1");
  elif [[ "$title" == *"P2"* || "$title_lc" == *"p2"* ]]; then labels+=("priority:P2");
  elif [[ "$title" == *"P3"* || "$title_lc" == *"p3"* ]]; then labels+=("priority:P3");
  else labels+=("priority:P2"); fi

  # type
  if [[ "$title_lc" == *"bug"* || "$title_lc" == *"fehler"* ]]; then labels+=("bug");
  elif [[ "$title_lc" == *"docs"* || "$title_lc" == *"doku"* || "$title_lc" == *"readme"* ]]; then labels+=("documentation");
  elif [[ "$title_lc" == *"test"* || "$title_lc" == *"e2e"* || "$title_lc" == *"smoke"* ]]; then labels+=("testing");
  else labels+=("enhancement"); fi

  # area
  if printf '%s' "$title" | grep -Eq "\b(UI|Frontend|React|Svelte|CSS|UX)\b"; then labels+=("area:ui");
  elif printf '%s' "$title" | grep -Eq "\b(API|Backend|Endpoint|Service|Route)\b"; then labels+=("area:api"); fi

  # apply labels
  edit_args=()
  for label in "${labels[@]}"; do
    edit_args+=(--add-label "$label")
  done
  gh issue edit "$num" --repo "$REPO" "${edit_args[@]}"

  labelled+=("$num")
done

# summary
printf 'SUMMARY_CHECKED:%d
' "$checked"
printf 'SUMMARY_LABELLED:%d
' "${#labelled[@]}"
printf 'LABELLED_ISSUES:%s
' "${labelled[*]}"
