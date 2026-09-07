"""The schema/seed bootstrap that runs on a cold start."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from app.database import SessionLocal, initialise_database
from app.models import Category, Product

RUNNER = """
import sys
from app.database import initialise_database
try:
    initialise_database()
    print("OK")
except Exception as exc:
    print(f"{type(exc).__name__}: {exc}")
    sys.exit(1)
"""


def _counts() -> tuple[int, int]:
    with SessionLocal() as session:
        return (
            int(session.scalar(select(func.count()).select_from(Category)) or 0),
            int(session.scalar(select(func.count()).select_from(Product)) or 0),
        )


def test_running_the_bootstrap_again_changes_nothing() -> None:
    from app import database

    before = _counts()

    # Force the once-per-process guard open, as a fresh cold start would.
    database._initialised = False
    initialise_database()

    assert _counts() == before == (6, 24)


@pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="the cold-start race is Postgres-specific; set TEST_DATABASE_URL to run it",
)
def test_concurrent_cold_starts_do_not_collide(tmp_path) -> None:
    """Four processes bootstrapping one empty database must all succeed.

    Without the advisory lock, concurrent `CREATE TABLE` statements fail each
    other with a unique violation on Postgres's own catalogue — which is exactly
    what a first deployment under traffic looks like.
    """
    url = os.environ["TEST_DATABASE_URL"]
    base, _, name = url.rpartition("/")
    race_url = f"{base}/{name}_race"

    import psycopg

    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(f'DROP DATABASE IF EXISTS "{name}_race"')
        connection.execute(f'CREATE DATABASE "{name}_race"')

    environment = {**os.environ, "DATABASE_URL": race_url}
    environment.pop("TEST_DATABASE_URL", None)

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", RUNNER],
            capture_output=True,
            check=False,
            text=True,
            env=environment,
            cwd=os.getcwd(),
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: run(), range(4)))

    assert all(result.returncode == 0 for result in results), [r.stdout + r.stderr for r in results]
