"""Database engine and session handling.

Serverless-shaped on purpose. On Vercel the backend runs as a Function, so a
long-lived connection pool is worse than useless: instances are frozen and
thawed, and a pooled connection held across invocations is likely to be dead by
the time it is reused. ``NullPool`` opens and closes a connection per checkout,
and the pooling is left to the managed Postgres pooler on the other end of the
connection string.

SQLAlchemy documents NullPool as the pool "which does not pool connections...
it literally opens and closes the underlying DB-API connection per each
connection open/close":
https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.NullPool
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

#: Drivers that providers hand out which SQLAlchemy 2.x will not accept as-is.
_LEGACY_PREFIXES = ("postgres://", "postgresql://")
#: The psycopg 3 dialect. Verified: this URL resolves to PGDialect_psycopg.
_TARGET_PREFIX = "postgresql+psycopg://"


def normalise_database_url(url: str) -> str:
    """Point any Postgres URL at the psycopg 3 driver.

    Managed providers usually hand out ``postgres://...``, which SQLAlchemy 2.x
    rejects, or bare ``postgresql://...``, which would select psycopg2. Query
    parameters such as ``?sslmode=require`` are preserved untouched.
    """
    for prefix in _LEGACY_PREFIXES:
        if url.startswith(prefix):
            return _TARGET_PREFIX + url[len(prefix) :]
    return url


def build_engine(url: str) -> Engine:
    """Create an engine with pooling disabled."""
    return create_engine(
        normalise_database_url(url),
        poolclass=NullPool,
        future=True,
        # Money is NUMERIC in the database and Decimal in Python. Never float.
        connect_args={},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide engine built from settings."""
    settings = get_settings()
    if not settings.uses_database:
        msg = "DATABASE_URL is not set"
        raise RuntimeError(msg)
    return build_engine(settings.database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Run a unit of work in a transaction, rolling back on failure."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
