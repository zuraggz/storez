"""Small admin CLI.

    python -m app.cli init     create the schema and seed demo data
    python -m app.cli seed     seed only (skips tables that already have rows)
    python -m app.cli check    report which database the app would talk to
    python -m app.cli reset    drop every table, then recreate and seed
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import func, select

from app import database
from app.config import get_settings
from app.database import database_is_reachable, engine, initialise_database, session_scope
from app.models import Base, BlogPost, Category, ContactMessage, Product, Subscriber
from app.seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger("qlonil.cli")


def _redacted_url() -> str:
    """The database URL with any password removed, safe to print."""
    url = engine.url
    return url.render_as_string(hide_password=True)


def command_init() -> int:
    # The same locked bootstrap the app runs on a cold start.
    initialise_database(seed=True)

    logger.info("Schema created and demo data seeded into %s", _redacted_url())
    return 0


def command_seed() -> int:
    with session_scope() as session:
        seed_database(session)

    logger.info("Seeding complete")
    return 0


def command_check() -> int:
    settings = get_settings()
    print(f"database   {_redacted_url()}")
    print(f"dialect    {engine.dialect.name}")
    print(f"reachable  {database_is_reachable()}")

    if settings.is_sqlite:
        print(
            "\nNote: SQLite is the local fallback. Vercel's filesystem is read-only and\n"
            "ephemeral, so set DATABASE_URL to a Postgres URL before deploying."
        )
        return 0

    with session_scope() as session:
        for model in (Category, Product, BlogPost, Subscriber, ContactMessage):
            count = session.scalar(select(func.count()).select_from(model))
            print(f"{model.__tablename__:<18} {count}")

    return 0


def command_reset(force: bool) -> int:
    if not force:
        logger.error("Refusing to drop every table without --force")
        return 1

    Base.metadata.drop_all(bind=engine)
    logger.info("Dropped all tables")

    # The bootstrap only runs once per process; the tables it created are gone.
    database._initialised = False

    return command_init()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="create the schema and seed demo data")
    subparsers.add_parser("seed", help="seed demo data into empty tables")
    subparsers.add_parser("check", help="show the configured database and row counts")

    reset = subparsers.add_parser("reset", help="drop every table, then recreate and seed")
    reset.add_argument("--force", action="store_true", help="required: this deletes all data")

    args = parser.parse_args(argv)

    match args.command:
        case "init":
            return command_init()
        case "seed":
            return command_seed()
        case "check":
            return command_check()
        case "reset":
            return command_reset(args.force)

    return 1


if __name__ == "__main__":
    sys.exit(main())
