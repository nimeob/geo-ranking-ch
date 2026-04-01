#!/usr/bin/env bash
# Shared route matrix for UI login-start + live auth/analyze smoke checks.

GUI_SMOKE_ROUTES=(
  "/"
  "/gui"
  "/gui/history"
  "/gui?view=trace&request_id=req-smoke"
  "/history"
  "/jobs"
  "/jobs?source=smoke"
  "/jobs/demo-job"
  "/results"
  "/results/demo-result"
  "/results/demo-result?tab=raw&source=smoke"
  "/gui/results"
  "/gui/results/demo-result"
  "/gui/results/demo-result?tab=raw&source=smoke"
  "/gui/jobs"
  "/gui/jobs?source=smoke"
  "/gui/jobs/demo-job"
)

GUI_SMOKE_SELECTED_ROUTES=()
GUI_SMOKE_SELECTED_PRESETS=()

gui_smoke_trim_whitespace() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

gui_smoke_route_is_supported() {
  local route="${1:-}"
  local candidate=""

  for candidate in "${GUI_SMOKE_ROUTES[@]}"; do
    if [[ "${candidate}" == "${route}" ]]; then
      return 0
    fi
  done

  return 1
}

gui_smoke_supported_routes_csv() {
  local IFS=','
  printf '%s' "${GUI_SMOKE_ROUTES[*]}"
}

gui_smoke_print_supported_routes_hint() {
  local supported_routes_csv=""

  supported_routes_csv="$(gui_smoke_supported_routes_csv)"
  if [[ -n "${supported_routes_csv}" ]]; then
    echo "HINT: Supported routes: ${supported_routes_csv}" >&2
  fi
}

gui_smoke_supported_route_presets_csv() {
  echo "all,core,modern,legacy,jobs,results,trace,minimal"
}

gui_smoke_print_supported_route_presets_hint() {
  local supported_presets_csv=""

  supported_presets_csv="$(gui_smoke_supported_route_presets_csv)"
  if [[ -n "${supported_presets_csv}" ]]; then
    echo "HINT: Supported route presets: ${supported_presets_csv}" >&2
  fi
}

gui_smoke_route_preset_is_supported() {
  local preset="${1:-}"

  case "${preset}" in
    all|core|modern|legacy|jobs|results|trace|minimal)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

gui_smoke_routes_for_preset() {
  local preset="${1:-}"

  case "${preset}" in
    all)
      printf '%s\n' "${GUI_SMOKE_ROUTES[@]}"
      ;;
    core)
      cat <<'EOF'
/
/gui
/history
/jobs
/results
EOF
      ;;
    modern)
      cat <<'EOF'
/
/gui
/history
/gui?view=trace&request_id=req-smoke
/jobs
/jobs?source=smoke
/jobs/demo-job
/results
/results/demo-result
/results/demo-result?tab=raw&source=smoke
EOF
      ;;
    legacy)
      cat <<'EOF'
/gui/history
/gui/jobs
/gui/jobs?source=smoke
/gui/jobs/demo-job
/gui/results
/gui/results/demo-result
/gui/results/demo-result?tab=raw&source=smoke
EOF
      ;;
    jobs)
      cat <<'EOF'
/jobs
/jobs?source=smoke
/jobs/demo-job
/gui/jobs
/gui/jobs?source=smoke
/gui/jobs/demo-job
EOF
      ;;
    results)
      cat <<'EOF'
/results
/results/demo-result
/results/demo-result?tab=raw&source=smoke
/gui/results
/gui/results/demo-result
/gui/results/demo-result?tab=raw&source=smoke
EOF
      ;;
    trace)
      echo "/gui?view=trace&request_id=req-smoke"
      ;;
    minimal)
      cat <<'EOF'
/
/gui
EOF
      ;;
    *)
      return 1
      ;;
  esac
}

gui_smoke_selected_presets_csv() {
  local IFS=','
  printf '%s' "${GUI_SMOKE_SELECTED_PRESETS[*]}"
}

gui_smoke_parse_route_csv() {
  local raw_csv="${1:-}"
  local token=""
  local route=""

  declare -A _seen_routes=()
  GUI_SMOKE_SELECTED_ROUTES=()

  if [[ -z "${raw_csv}" ]]; then
    if (( ${#GUI_SMOKE_ROUTES[@]} == 0 )); then
      echo "ERROR: GUI_SMOKE_ROUTES is empty" >&2
      return 1
    fi

    GUI_SMOKE_SELECTED_ROUTES=("${GUI_SMOKE_ROUTES[@]}")
    return 0
  fi

  IFS=',' read -r -a _route_tokens <<< "${raw_csv}"
  for token in "${_route_tokens[@]}"; do
    route="$(gui_smoke_trim_whitespace "${token}")"
    [[ -n "${route}" ]] || continue

    if [[ "${route}" != /* ]]; then
      echo "ERROR: Invalid route token: ${route} (routes must start with '/')" >&2
      gui_smoke_print_supported_routes_hint
      return 1
    fi

    if ! gui_smoke_route_is_supported "${route}"; then
      echo "ERROR: Unsupported route token: ${route}" >&2
      gui_smoke_print_supported_routes_hint
      return 1
    fi

    if [[ -z "${_seen_routes["${route}"]+x}" ]]; then
      GUI_SMOKE_SELECTED_ROUTES+=("${route}")
      _seen_routes["${route}"]=1
    fi
  done

  if (( ${#GUI_SMOKE_SELECTED_ROUTES[@]} == 0 )); then
    echo "ERROR: --routes produced an empty route list" >&2
    return 1
  fi
}

gui_smoke_parse_route_presets_csv() {
  local raw_csv="${1:-}"
  local token=""
  local preset=""
  local route=""

  declare -A _seen_presets=()
  declare -A _seen_routes=()
  GUI_SMOKE_SELECTED_PRESETS=()
  GUI_SMOKE_SELECTED_ROUTES=()

  if [[ -z "${raw_csv}" ]]; then
    echo "ERROR: --route-presets produced an empty preset list" >&2
    gui_smoke_print_supported_route_presets_hint
    return 1
  fi

  IFS=',' read -r -a _preset_tokens <<< "${raw_csv}"
  for token in "${_preset_tokens[@]}"; do
    preset="$(gui_smoke_trim_whitespace "${token}")"
    preset="${preset,,}"
    [[ -n "${preset}" ]] || continue

    if ! gui_smoke_route_preset_is_supported "${preset}"; then
      echo "ERROR: Unsupported route preset: ${preset}" >&2
      gui_smoke_print_supported_route_presets_hint
      return 1
    fi

    if [[ -z "${_seen_presets["${preset}"]+x}" ]]; then
      GUI_SMOKE_SELECTED_PRESETS+=("${preset}")
      _seen_presets["${preset}"]=1
    fi

    while IFS= read -r route; do
      [[ -n "${route}" ]] || continue

      if ! gui_smoke_route_is_supported "${route}"; then
        echo "ERROR: Route preset '${preset}' resolved to unsupported route token: ${route}" >&2
        gui_smoke_print_supported_routes_hint
        return 1
      fi

      if [[ -z "${_seen_routes["${route}"]+x}" ]]; then
        GUI_SMOKE_SELECTED_ROUTES+=("${route}")
        _seen_routes["${route}"]=1
      fi
    done < <(gui_smoke_routes_for_preset "${preset}")
  done

  if (( ${#GUI_SMOKE_SELECTED_PRESETS[@]} == 0 )); then
    echo "ERROR: --route-presets produced an empty preset list" >&2
    gui_smoke_print_supported_route_presets_hint
    return 1
  fi

  if (( ${#GUI_SMOKE_SELECTED_ROUTES[@]} == 0 )); then
    echo "ERROR: --route-presets produced an empty route list" >&2
    return 1
  fi
}

gui_login_start_artifact_suffix_for_route() {
  local route="${1:-}"

  case "${route}" in
    "/")
      echo "login-start-smoke-root"
      ;;
    "/gui")
      echo "login-start-smoke"
      ;;
    "/gui/history")
      echo "login-start-smoke-gui-history"
      ;;
    "/gui?view=trace&request_id=req-smoke")
      echo "login-start-smoke-gui-trace-view"
      ;;
    "/history")
      echo "login-start-smoke-history-legacy"
      ;;
    "/jobs")
      echo "login-start-smoke-jobs"
      ;;
    "/jobs?source=smoke")
      echo "login-start-smoke-jobs-query"
      ;;
    "/jobs/demo-job")
      echo "login-start-smoke-jobs-detail"
      ;;
    "/results")
      echo "login-start-smoke-results"
      ;;
    "/results/demo-result")
      echo "login-start-smoke-results-detail"
      ;;
    "/results/demo-result?tab=raw&source=smoke")
      echo "login-start-smoke-results-detail-query"
      ;;
    "/gui/results")
      echo "login-start-smoke-gui-results-legacy"
      ;;
    "/gui/results/demo-result")
      echo "login-start-smoke-gui-results-legacy-detail"
      ;;
    "/gui/results/demo-result?tab=raw&source=smoke")
      echo "login-start-smoke-gui-results-legacy-detail-query"
      ;;
    "/gui/jobs")
      echo "login-start-smoke-gui-jobs-legacy"
      ;;
    "/gui/jobs?source=smoke")
      echo "login-start-smoke-gui-jobs-legacy-query"
      ;;
    "/gui/jobs/demo-job")
      echo "login-start-smoke-gui-jobs-legacy-detail"
      ;;
    *)
      return 1
      ;;
  esac
}

gui_canonical_redirect_artifact_suffix_for_route() {
  local route="${1:-}"
  local login_suffix=""

  login_suffix="$(gui_login_start_artifact_suffix_for_route "${route}")" || return 1
  echo "${login_suffix/login-start-smoke/canonical-host-redirect-smoke}"
}
