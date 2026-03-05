#!/usr/bin/env bash
set -euo pipefail
GH_TOKEN=$(./scripts/gh_app_token.sh)
# Authenticate
echo "$GH_TOKEN" | gh auth login --with-token >/dev/null 2>&1 || true
ISSUES_JSON=$(gh issue list --state open --json number,title,labels --repo nimeob/geo-ranking-ch)
readarray -t items < <(echo "$ISSUES_JSON" | jq -c '.[] | select((.labels | length) == 0)')
count_checked=0
count_labeled=0
labeled_nums=()
for issue in "${items[@]}"; do
  count_checked=$((count_checked+1))
  num=$(echo "$issue" | jq -r '.number')
  title_orig=$(echo "$issue" | jq -r '.title')
  title=$(echo "$title_orig" | tr '[:upper:]' '[:lower:]')
  if echo "$title" | grep -q 'p0'; then prio='priority:P0'
  elif echo "$title" | grep -q 'p1'; then prio='priority:P1'
  elif echo "$title" | grep -q 'p2'; then prio='priority:P2'
  elif echo "$title" | grep -q 'p3'; then prio='priority:P3'
  else prio='priority:P2'; fi
  if echo "$title" | grep -qE 'bug|fehler'; then typ='bug'
  elif echo "$title" | grep -qE 'docs|doku|readme'; then typ='documentation'
  elif echo "$title" | grep -qE 'test|e2e|smoke'; then typ='testing'
  else typ='enhancement'; fi
  if echo "$title" | grep -qE 'ui|frontend|react|svelte|css|ux'; then area='area:ui'
  elif echo "$title" | grep -qE 'api|backend|endpoint|service|route'; then area='area:api'
  else area=''
  fi
  labels=(backlog "status:todo" "$prio" "$typ")
  if [ -n "$area" ]; then labels+=("$area"); fi
  labels_csv=$(IFS=,; echo "${labels[*]}")
  gh issue edit "$num" --repo nimeob/geo-ranking-ch --add-label "$labels_csv" && 
    count_labeled=$((count_labeled+1)) && labeled_nums+=("$num") || true
  sleep 0.2
done
echo "CHECKED:$count_checked LABELED:$count_labeled"
if [ ${#labeled_nums[@]} -gt 0 ]; then echo "LABELED_ISSUES: ${labeled_nums[*]}"; fi
