"""Test fixtures.

The environment is set before `app` is imported, because the engine is built
from the settings at import time. Each run gets its own SQLite file, seeded with
the same demo data the storefront ships.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="qlonil-tests-"))

# Point TEST_DATABASE_URL at a Postgres instance to run the same suite against
# the engine production uses; otherwise each run gets its own SQLite file.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", f"sqlite:///{(_TEMP_DIR / 'test.db').as_posix()}"
)
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTO_INIT_DB"] = "true"
os.environ["SEED_DEMO_DATA"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import initialise_database  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    initialise_database()


@pytest.fixture()
def unique_email() -> str:
    """A never-seen-before address, so signup tests can be re-run on one database."""
    return f"reader-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
