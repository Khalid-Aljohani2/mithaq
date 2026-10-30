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

#: Passed to psycopg on every connection this module opens.
#:
#: ``prepare_threshold=None`` disables automatic prepared statements. This is
#: mandatory in production: Supabase's shared pooler in **transaction mode**
#: (port 6543) hands the same client connection a different server session
#: between statements, so a prepared statement created on one session is simply
#: not there on the next, and the query fails.
#:
#: psycopg states it directly: "Unless a connection pooling middleware
#: explicitly declares otherwise, they are not compatible with prepared
#: statements... If such middleware is used you should disable prepared
#: statements, by setting the Connection.prepare_threshold attribute to None."
#: https://www.psycopg.org/psycopg3/docs/advanced/prepare.html
#:
#: It is set unconditionally rather than only for port 6543, because the cost
#: is a little lost statement caching and the failure mode is a production-only
#: error that local development would never reproduce.
CONNECT_ARGS: dict[str, object] = {"prepare_threshold": None}


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
    """Create an engine with pooling disabled and prepared statements off."""
    return create_engine(
        normalise_database_url(url),
        poolclass=NullPool,
        future=True,
        connect_args=dict(CONNECT_ARGS),
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
