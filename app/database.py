"""Engine, session factory and the one-shot schema bootstrap.

Serverless functions get a fresh process per cold start and may run many
concurrently, so the engine uses NullPool: every request opens and closes its
own connection instead of holding one open against the database's connection
limit. Neon's pooled endpoint (`-pooler` in the host name) does the pooling for
us.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger("qlonil.database")

settings = get_settings()

_connect_args: dict[str, object] = {}
if settings.is_sqlite:
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    future=True,
    pool_pre_ping=not settings.is_sqlite,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

# Guards the bootstrap so concurrent requests in one process only run it once.
_init_lock = threading.Lock()
_initialised = False


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session for scripts and startup code, committed or rolled back."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


#: Any stable 64-bit key works; this one is arbitrary and specific to this app.
_ADVISORY_LOCK_KEY = 1279414604


def _bootstrap(connection: Connection, should_seed: bool) -> None:
    """Create the schema and seed, on one connection, inside whatever lock holds."""
    from app import models  # noqa: F401  (registers the mappers)
    from app.models import Base
    from app.seed import seed_database

    Base.metadata.create_all(bind=connection)
    connection.commit()

    if should_seed:
        with Session(bind=connection) as session:
            seed_database(session)
            session.commit()


def initialise_database(seed: bool | None = None) -> None:
    """Create the schema and seed demo data once per process.

    Several cold starts can land here at once against an empty database. Two
    concurrent `CREATE TABLE` statements do not merely duplicate work — Postgres
    fails one of them with a unique violation on its own catalogue — and two
    concurrent seeders would each see empty tables. So on Postgres the whole
    bootstrap runs under a session-level advisory lock: the first process
    creates and seeds, the others wait and then find the work already done.
    SQLite is a single-writer file used only for local development.
    """
    global _initialised

    if _initialised:
        return

    with _init_lock:
        if _initialised:
            return

        should_seed = get_settings().seed_demo_data if seed is None else seed

        if settings.is_sqlite:
            with engine.connect() as connection:
                _bootstrap(connection, should_seed)
        else:
            with engine.connect() as connection:
                connection.execute(
                    text("SELECT pg_advisory_lock(:key)"), {"key": _ADVISORY_LOCK_KEY}
                )
                connection.commit()
                try:
                    _bootstrap(connection, should_seed)
                finally:
                    connection.rollback()
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": _ADVISORY_LOCK_KEY}
                    )
                    connection.commit()

        _initialised = True
        logger.info("Database ready")


def database_is_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - exercised by the health endpoint
        logger.exception("Database round-trip failed")
        return False
