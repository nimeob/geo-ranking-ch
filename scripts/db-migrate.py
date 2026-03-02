#!/usr/bin/env python3
"""
db-migrate.py — Minimal idempotent Postgres migration runner.

Usage:
    python scripts/db-migrate.py [--dry-run] [--apply] [--status] [--target VERSION]
    python scripts/db-migrate.py --apply
    python scripts/db-migrate.py --dry-run
    python scripts/db-migrate.py --status

Environment:
    DATABASE_URL   postgresql://user:pass@host:5432/dbname  (required)

Migration files:
    db/migrations/<NNN>_<name>.sql   (e.g. 001_core_schema.sql)
    Files are applied in lexicographic order by filename.

Tracking table (created automatically in the target DB):
    schema_migrations (version TEXT PK, applied_at TIMESTAMPTZ, checksum TEXT)

Exit codes:
    0 — success (or dry-run complete)
    1 — error (connection failure, SQL error, checksum mismatch)
    2 — pending migrations exist (only when --check flag used)

Issue: #813 (DB-0.wp2)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"
TRACKING_TABLE = "schema_migrations"

CREATE_TRACKING_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
    version    text        PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now(),
    checksum   text        NOT NULL,
    filename   text        NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        print("  Example: export DATABASE_URL=postgresql://georanking:dev_only_change_me@localhost:5432/georanking_dev", file=sys.stderr)
        sys.exit(1)
    return url


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_migration_files() -> list[tuple[str, Path]]:
    """
    Return sorted list of (version, path) for all *.sql files in MIGRATIONS_DIR.
    Version is the filename stem (e.g. '001_core_schema').
    """
    if not MIGRATIONS_DIR.exists():
        print(f"ERROR: Migrations directory not found: {MIGRATIONS_DIR}", file=sys.stderr)
        sys.exit(1)
    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)
    return [(p.stem, p) for p in files]


def connect(db_url: str):
    """
    Connect to Postgres. Returns a psycopg2 connection.
    Raises ImportError with a helpful message if psycopg2 is not installed.
    """
    try:
        import psycopg2  # type: ignore
    except ImportError:
        print("ERROR: psycopg2-binary is required to run this script.", file=sys.stderr)
        print("  Install: pip install psycopg2-binary", file=sys.stderr)
        print("  Or: pip install -r requirements-dev.txt", file=sys.stderr)
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        return conn
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Could not connect to database: {exc}", file=sys.stderr)
        print("  Check DATABASE_URL and that the Postgres server is running.", file=sys.stderr)
        print("  Locally: ./scripts/db-local.sh start", file=sys.stderr)
        sys.exit(1)


def ensure_tracking_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_TRACKING_TABLE_SQL)
    conn.commit()


def get_applied_versions(conn) -> dict[str, str]:
    """Return {version: checksum} for all applied migrations."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT version, checksum FROM {TRACKING_TABLE} ORDER BY version")
        return {row[0]: row[1] for row in cur.fetchall()}


def record_migration(conn, version: str, checksum: str, filename: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TRACKING_TABLE} (version, applied_at, checksum, filename) VALUES (%s, %s, %s, %s)",
            (version, datetime.now(timezone.utc), checksum, filename),
        )
    conn.commit()


def apply_sql_file(conn, path: Path) -> None:
    """Execute a SQL file inside its own transaction."""
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(db_url: str) -> None:
    migrations = collect_migration_files()
    conn = connect(db_url)
    try:
        ensure_tracking_table(conn)
        applied = get_applied_versions(conn)
    finally:
        conn.close()

    print(f"{'VERSION':<40}  {'STATUS':<12}  {'CHECKSUM (first 12)'}")
    print("-" * 75)
    for version, path in migrations:
        if version in applied:
            checksum_short = applied[version][:12]
            status = "applied ✓"
        else:
            checksum_short = file_checksum(path)[:12]
            status = "PENDING"
        print(f"{version:<40}  {status:<12}  {checksum_short}")

    pending = [v for v, _ in migrations if v not in applied]
    print()
    if pending:
        print(f"→ {len(pending)} pending migration(s).")
    else:
        print("→ All migrations applied.")


def cmd_dry_run(db_url: str, target: str | None = None) -> None:
    migrations = collect_migration_files()
    conn = connect(db_url)
    try:
        ensure_tracking_table(conn)
        applied = get_applied_versions(conn)
    finally:
        conn.close()

    # Detect checksum mismatches for already-applied migrations
    for version, path in migrations:
        if version in applied:
            current = file_checksum(path)
            if current != applied[version]:
                print(f"WARNING: Checksum mismatch for applied migration '{version}'", file=sys.stderr)
                print(f"  Stored:  {applied[version]}", file=sys.stderr)
                print(f"  Current: {current}", file=sys.stderr)

    pending = [
        (v, p) for v, p in migrations
        if v not in applied and (target is None or v <= target)
    ]

    if not pending:
        print("[dry-run] No pending migrations.")
        return

    print(f"[dry-run] Would apply {len(pending)} migration(s):")
    for version, path in pending:
        size = path.stat().st_size
        checksum = file_checksum(path)[:12]
        print(f"  → {version}  ({size} bytes, sha256:{checksum}...)")


def cmd_apply(db_url: str, target: str | None = None, check_only: bool = False) -> None:
    migrations = collect_migration_files()
    conn = connect(db_url)
    try:
        ensure_tracking_table(conn)
        applied = get_applied_versions(conn)

        # Validate checksums of already-applied migrations
        mismatch = False
        for version, path in migrations:
            if version in applied:
                current = file_checksum(path)
                if current != applied[version]:
                    print(f"ERROR: Checksum mismatch for applied migration '{version}'.", file=sys.stderr)
                    print(f"  Stored:  {applied[version]}", file=sys.stderr)
                    print(f"  Current: {current}", file=sys.stderr)
                    print("  Migration files must not be modified after they are applied.", file=sys.stderr)
                    mismatch = True
        if mismatch:
            sys.exit(1)

        pending = [
            (v, p) for v, p in migrations
            if v not in applied and (target is None or v <= target)
        ]

        if not pending:
            print("✅ No pending migrations. Database is up to date.")
            return

        if check_only:
            print(f"❌ {len(pending)} pending migration(s) found (--check mode).")
            for version, _ in pending:
                print(f"   → {version}")
            sys.exit(2)

        print(f"Applying {len(pending)} migration(s)...")
        for version, path in pending:
            print(f"  → {version} ...", end=" ", flush=True)
            checksum = file_checksum(path)
            apply_sql_file(conn, path)
            record_migration(conn, version, checksum, path.name)
            print("✓")

        print(f"\n✅ {len(pending)} migration(s) applied successfully.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal idempotent Postgres migration runner (geo-ranking-ch)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--apply",
        action="store_true",
        help="Apply all pending migrations.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show what would be applied without executing.",
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Show applied vs. pending migration status.",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 2 if any migrations are pending (use in CI gates).",
    )
    parser.add_argument(
        "--target",
        metavar="VERSION",
        default=None,
        help="Apply/dry-run up to and including this version (e.g. 002_async_jobs_schema).",
    )
    parser.add_argument(
        "--db-url",
        metavar="URL",
        default=None,
        help="Postgres DSN. Overrides DATABASE_URL env var.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db_url = args.db_url if args.db_url else get_db_url()

    if args.status:
        cmd_status(db_url)
    elif args.dry_run:
        cmd_dry_run(db_url, target=args.target)
    elif args.apply:
        cmd_apply(db_url, target=args.target)
    elif args.check:
        cmd_apply(db_url, target=args.target, check_only=True)


if __name__ == "__main__":
    main()
