"""Shared FastAPI dependencies."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, initialise_database

logger = logging.getLogger("qlonil.deps")


def get_db() -> Iterator[Session]:
    """A session per request, with a one-time schema bootstrap in front of it.

    Serverless cold starts can arrive before the database exists, and the
    lifespan hook deliberately swallows a failure there rather than taking the
    app down — so the first request that gets through tries again. After the
    first success this is a boolean check.
    """
    if get_settings().auto_init_db:
        initialise_database()

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
