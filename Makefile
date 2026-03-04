SHELL := /usr/bin/env bash

.PHONY: dev-smoke dev-check

dev-smoke:
	@set -euo pipefail; \
	SMOKE_SCRIPT="./scripts/check_bl334_split_smokes.sh"; \
	PYTHON_BIN="$${PYTHON_BIN:-python3}"; \
	CURL_BIN="$${CURL_BIN:-curl}"; \
	if ! command -v "$$PYTHON_BIN" >/dev/null 2>&1; then \
		echo "ERROR: required command not found: $$PYTHON_BIN" >&2; \
		exit 2; \
	fi; \
	if ! command -v "$$CURL_BIN" >/dev/null 2>&1; then \
		echo "ERROR: required command not found: $$CURL_BIN" >&2; \
		exit 2; \
	fi; \
	if [[ ! -x "$$SMOKE_SCRIPT" ]]; then \
		echo "ERROR: missing or non-executable smoke script: $$SMOKE_SCRIPT" >&2; \
		exit 2; \
	fi; \
	echo "[dev-smoke] Running $$SMOKE_SCRIPT"; \
	PYTHON_BIN="$$PYTHON_BIN" CURL_BIN="$$CURL_BIN" "$$SMOKE_SCRIPT"

# Einheitlicher lokaler Pre-PR Check (Lint + Type/Syntax + Unit-Tests).
dev-check:
	@./scripts/check_dev_quality_gate.sh
