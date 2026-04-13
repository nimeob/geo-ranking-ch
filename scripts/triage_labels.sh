#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GHA_BIN="${SCRIPT_DIR}/gha"
if [[ ! -x "$GHA_BIN" ]]; then
  GHA_BIN="gh"
fi

REPO="nimeob/geo-ranking-ch"
LIMIT="${TRIAGE_LABELS_LIMIT:-200}"

issues_json="$($GHA_BIN issue list --repo "$REPO" --state open --limit "$LIMIT" --json number,title,labels)"
count_checked="$(printf '%s' "$issues_json" | jq 'length')"

count_to_label=0
labeled_nums=""

while IFS= read -r row; do
  num="$(printf '%s' "$row" | jq -r '.number')"
  title="$(printf '%s' "$row" | jq -r '.title')"

  pri="priority:P2"
  if [[ "$title" == *P0* || "$title" == *p0* ]]; then
    pri="priority:P0"
  elif [[ "$title" == *P1* || "$title" == *p1* ]]; then
    pri="priority:P1"
  elif [[ "$title" == *P2* || "$title" == *p2* ]]; then
    pri="priority:P2"
  elif [[ "$title" == *P3* || "$title" == *p3* ]]; then
    pri="priority:P3"
  fi

  lc="$(echo "$title" | tr '[:upper:]' '[:lower:]')"
  if echo "$lc" | grep -q -e "bug" -e "fehler"; then
    typ="bug"
  elif echo "$lc" | grep -q -e "docs" -e "doku" -e "readme"; then
    typ="documentation"
  elif echo "$lc" | grep -q -e "test" -e "e2e" -e "smoke"; then
    typ="testing"
  else
    typ="enhancement"
  fi

  area=""
  if echo "$title" | grep -q -e "UI" -e "Frontend" -e "React" -e "Svelte" -e "CSS" -e "UX"; then
    area="area:ui"
  elif echo "$title" | grep -q -e "API" -e "Backend" -e "Endpoint" -e "Service" -e "Route"; then
    area="area:api"
  fi

  labels_csv="backlog,status:todo,$pri,$typ"
  if [[ -n "$area" ]]; then
    labels_csv="$labels_csv,$area"
  fi

  $GHA_BIN issue edit "$num" --repo "$REPO" --add-label "$labels_csv"
  count_to_label=$((count_to_label + 1))
  labeled_nums="$labeled_nums $num"
done < <(printf '%s' "$issues_json" | jq -c '.[] | select((.labels | length) == 0)')

printf "checked=%s\nlabelled=%s\nnums=%s\n" "$count_checked" "$count_to_label" "$labeled_nums"
