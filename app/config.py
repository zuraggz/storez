"""Configuration, read once from the environment.

Every deployment knob lives here so the rest of the app never touches os.environ
directly. `.env` is loaded when present, which covers local development; on
Vercel the same names are set as project environment variables.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PUBLIC_DIR = PROJECT_ROOT / "public"

load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalise_database_url(url: str) -> str:
    """Make any Postgres URL a SQLAlchemy + psycopg 3 URL.

    Neon, Supabase, Railway and Heroku all hand out `postgres://` or
    `postgresql://` URLs, which SQLAlchemy would route to psycopg2. This project
    ships psycopg 3, so the driver is pinned explicitly.
    """
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    cors_allowed_origins: tuple[str, ...]
    auto_init_db: bool
    seed_demo_data: bool
    site_name: str = "Qlonil"
    contact_email: str = "business@qlonil.com"
    contact_phone: str = "+00 123 456 789"
    # The en dash is the design's own copy, not a typo.
    contact_address: tuple[str, ...] = field(
        default=("No. 651 – London Oxford Street,", "819 United Kingdom.")  # noqa: RUF001
    )

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_exact_origins(self) -> list[str]:
        return [o for o in self.cors_allowed_origins if "*" not in o]

    @property
    def cors_origin_regex(self) -> str | None:
        """Translate `https://*.vercel.app` style entries into one regex.

        `*` stands for a single URL segment, so preview deployments are allowed
        while `https://evil.vercel.app.co` is not.
        """
        patterns = [o for o in self.cors_allowed_origins if "*" in o and o != "*"]
        if not patterns:
            return None
        alternatives = [re.escape(p).replace(r"\*", r"[^./:]+") for p in patterns]
        return "^(?:" + "|".join(alternatives) + ")$"

    @property
    def cors_allow_any_origin(self) -> bool:
        return "*" in self.cors_allowed_origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if raw_url:
        database_url = normalise_database_url(raw_url)
    else:
        # No database configured: fall back to a local SQLite file so the app
        # still runs end to end. Vercel's filesystem is read-only and ephemeral,
        # so a real DATABASE_URL is required there (see README).
        database_url = f"sqlite:///{(PROJECT_ROOT / 'qlonil.db').as_posix()}"

    origins = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
    )

    return Settings(
        environment=os.getenv("ENVIRONMENT", "production"),
        database_url=database_url,
        cors_allowed_origins=tuple(
            part.strip() for part in origins.split(",") if part.strip()
        ),
        auto_init_db=_bool("AUTO_INIT_DB", True),
        seed_demo_data=_bool("SEED_DEMO_DATA", True),
    )
