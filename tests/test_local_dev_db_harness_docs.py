from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.dev.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DB_LOCAL_SCRIPT = REPO_ROOT / "scripts" / "db-local.sh"
LOCAL_DEV_DOC = REPO_ROOT / "docs" / "local-dev.md"


class TestLocalDevDbHarnessDocs(unittest.TestCase):
    def test_compose_file_defines_postgres_with_healthcheck_and_volume(self):
        content = COMPOSE_FILE.read_text(encoding="utf-8")

        self.assertIn("services:", content)
        self.assertIn("postgres:", content)
        self.assertIn("image: postgres:16-alpine", content)
        self.assertIn("healthcheck:", content)
        self.assertIn("pg_isready", content)
        self.assertIn("volumes:", content)
        self.assertIn("georanking_dev_pgdata", content)

    def test_env_example_contains_local_database_url(self):
        content = ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn(
            "DATABASE_URL=postgresql://georanking:dev_only_change_me@localhost:5432/georanking_dev",
            content,
        )

    def test_db_local_script_is_shell_valid_and_includes_required_commands(self):
        cp = subprocess.run(
            ["bash", "-n", str(DB_LOCAL_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

        content = DB_LOCAL_SCRIPT.read_text(encoding="utf-8")
        for command in ["start)", "stop)", "reset)", "status)", "migrate)", "psql)"]:
            self.assertIn(command, content)

    def test_local_dev_doc_covers_start_migrate_and_smoke_flow(self):
        content = LOCAL_DEV_DOC.read_text(encoding="utf-8")

        self.assertIn("./scripts/db-local.sh start", content)
        self.assertIn("./scripts/db-local.sh migrate", content)
        self.assertIn("db-migrate.py --apply", content)
        self.assertIn("docker compose -f docker-compose.dev.yml exec postgres", content)
        self.assertIn("DATABASE_URL", content)


if __name__ == "__main__":
    unittest.main()
