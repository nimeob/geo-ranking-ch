#!/usr/bin/env bash
set -euo pipefail

marker_path="${DEV_UI_SMOKE_FALLBACK_MARKER_PATH:?missing DEV_UI_SMOKE_FALLBACK_MARKER_PATH}"
printf '%s\n' "${PWD}" > "${marker_path}"
printf 'fallback-ok\n'
