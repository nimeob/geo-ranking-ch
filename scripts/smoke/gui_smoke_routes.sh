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
  "/results/demo-result"
  "/results/demo-result?tab=raw&source=smoke"
  "/gui/results/demo-result"
  "/gui/results/demo-result?tab=raw&source=smoke"
  "/gui/jobs"
  "/gui/jobs?source=smoke"
  "/gui/jobs/demo-job"
)

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
    "/results/demo-result")
      echo "login-start-smoke-results-detail"
      ;;
    "/results/demo-result?tab=raw&source=smoke")
      echo "login-start-smoke-results-detail-query"
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
