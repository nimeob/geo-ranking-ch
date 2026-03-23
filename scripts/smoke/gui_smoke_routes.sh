#!/usr/bin/env bash
# Shared route matrix for UI login-start + live auth/analyze smoke checks.

GUI_SMOKE_ROUTES=(
  "/gui"
  "/gui/history"
  "/jobs"
  "/jobs?source=smoke"
  "/jobs/demo-job"
  "/results/demo-result"
  "/gui/jobs"
  "/gui/jobs?source=smoke"
  "/gui/jobs/demo-job"
)

gui_login_start_artifact_suffix_for_route() {
  local route="${1:-}"

  case "${route}" in
    "/gui")
      echo "login-start-smoke"
      ;;
    "/gui/history")
      echo "login-start-smoke-gui-history"
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
    "/results/demo-result")
      echo "login-start-smoke-results-detail"
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
