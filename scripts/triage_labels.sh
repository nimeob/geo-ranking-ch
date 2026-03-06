#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")" || exit 1
GH_APP_TOKEN=$(bash ./scripts/gh_app_token.sh)
if [ -z "$GH_APP_TOKEN" ]; then echo "NO_TOKEN" >&2; exit 2; fi
export GH_TOKEN="$GH_APP_TOKEN"
REPO="nimeob/geo-ranking-ch"
count_checked=$(gh issue list --repo "$REPO" --state open --json number --jq 'length')
issue_numbers=$(gh issue list --repo "$REPO" --state open --json number,title,labels --jq '.[] | select(.labels | length == 0) | .number')
count_to_label=0
labeled_nums=""
for num in $issue_numbers; do
  title=$(gh issue view "$num" --repo "$REPO" --json title --jq -r '.title')
  pri="priority:P2"
  if [[ "$title" == *P0* || "$title" == *p0* ]]; then pri="priority:P0";
  elif [[ "$title" == *P1* || "$title" == *p1* ]]; then pri="priority:P1";
  elif [[ "$title" == *P2* || "$title" == *p2* ]]; then pri="priority:P2";
  elif [[ "$title" == *P3* || "$title" == *p3* ]]; then pri="priority:P3"; fi
  lc=$(echo "$title" | tr '[:upper:]' '[:lower:]')
  if echo "$lc" | grep -q -e "bug" -e "fehler"; then typ="bug";
  elif echo "$lc" | grep -q -e "docs" -e "doku" -e "readme"; then typ="documentation";
  elif echo "$lc" | grep -q -e "test" -e "e2e" -e "smoke"; then typ="testing";
  else typ="enhancement"; fi
  area=""
  if echo "$title" | grep -q -e "UI" -e "Frontend" -e "React" -e "Svelte" -e "CSS" -e "UX"; then area="area:ui";
  elif echo "$title" | grep -q -e "API" -e "Backend" -e "Endpoint" -e "Service" -e "Route"; then area="area:api"; fi
  labels_csv="backlog,status:todo,$pri,$typ"
  if [ -n "$area" ]; then labels_csv="$labels_csv,$area"; fi
  gh issue edit "$num" --repo "$REPO" --add-label "$labels_csv"
  count_to_label=$((count_to_label+1))
  labeled_nums="$labeled_nums $num"
done
printf "checked=%s\nlabelled=%s\nnums=%s\n" "$count_checked" "$count_to_label" "$labeled_nums"
