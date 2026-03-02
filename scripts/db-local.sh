#!/usr/bin/env bash
# scripts/db-local.sh
# Start / Stop / Reset the local Postgres dev container.
#
# Issue: #833 (INFRA-DB-0.wp4)
# Requires: docker compose v2 (plugin), docker-compose.dev.yml in repo root.
#
# Usage:
#   ./scripts/db-local.sh start    — start Postgres, wait until healthy
#   ./scripts/db-local.sh stop     — stop container (data preserved)
#   ./scripts/db-local.sh reset    — destroy volume + restart (clean slate)
#   ./scripts/db-local.sh status   — show container status
#   ./scripts/db-local.sh migrate  — apply all SQL migrations in docs/sql/
#   ./scripts/db-local.sh psql     — open interactive psql shell

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.dev.yml"

# Load .env if present (but don't require it)
if [[ -f "${REPO_ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  set -o allexport
  source "${REPO_ROOT}/.env"
  set +o allexport
fi

POSTGRES_USER="${POSTGRES_USER:-georanking}"
POSTGRES_DB="${POSTGRES_DB:-georanking_dev}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

DC="docker compose -f ${COMPOSE_FILE}"

wait_healthy() {
  echo "⏳ Waiting for Postgres to be healthy..."
  local attempts=30
  for i in $(seq 1 "$attempts"); do
    if ${DC} exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
      echo "✅ Postgres is ready."
      return 0
    fi
    sleep 2
    echo "   attempt ${i}/${attempts}..."
  done
  echo "❌ Postgres did not become healthy in time." >&2
  return 1
}

cmd_start() {
  echo "🐘 Starting local dev Postgres..."
  ${DC} up -d postgres
  wait_healthy
  echo ""
  echo "  DSN: postgresql://${POSTGRES_USER}:<pass>@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
  echo "  Tip: Run ./scripts/db-local.sh migrate to apply schema migrations."
}

cmd_stop() {
  echo "🛑 Stopping local dev Postgres..."
  ${DC} stop postgres
  echo "✅ Stopped. Data volume preserved."
}

cmd_reset() {
  echo "⚠️  Resetting local dev Postgres (data will be DESTROYED)..."
  read -r -p "  Are you sure? (yes/no): " confirm
  if [[ "${confirm}" != "yes" ]]; then
    echo "Aborted."
    exit 0
  fi
  ${DC} down -v
  echo "🐘 Starting fresh Postgres..."
  ${DC} up -d postgres
  wait_healthy
  echo "✅ Clean slate ready."
}

cmd_status() {
  ${DC} ps postgres
}

cmd_migrate() {
  echo "🔄 Applying SQL migrations..."
  wait_healthy

  SQL_DIR="${REPO_ROOT}/docs/sql"
  if [[ ! -d "${SQL_DIR}" ]]; then
    echo "❌ No docs/sql/ directory found. Nothing to migrate." >&2
    exit 1
  fi

  local applied=0
  for sql_file in "${SQL_DIR}"/*.sql; do
    [[ -f "${sql_file}" ]] || continue
    echo "  → Applying $(basename "${sql_file}")..."
    ${DC} exec -T postgres psql \
      -U "${POSTGRES_USER}" \
      -d "${POSTGRES_DB}" \
      -f - < "${sql_file}"
    applied=$((applied + 1))
  done

  if [[ "${applied}" -eq 0 ]]; then
    echo "⚠️  No .sql files found in ${SQL_DIR}."
  else
    echo "✅ ${applied} migration file(s) applied."
  fi
}

cmd_psql() {
  wait_healthy
  echo "🐘 Connecting to ${POSTGRES_DB}..."
  ${DC} exec postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
}

usage() {
  echo "Usage: $0 {start|stop|reset|status|migrate|psql}"
  exit 1
}

case "${1:-}" in
  start)   cmd_start   ;;
  stop)    cmd_stop    ;;
  reset)   cmd_reset   ;;
  status)  cmd_status  ;;
  migrate) cmd_migrate ;;
  psql)    cmd_psql    ;;
  *)       usage       ;;
esac
