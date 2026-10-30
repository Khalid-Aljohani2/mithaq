"""Engine configuration tests.

The one that matters is
:func:`test_live_connection_has_prepared_statements_disabled`: it opens a real
connection and inspects the psycopg object, rather than trusting that a keyword
argument reached the driver.
"""

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.pool import NullPool

from app.db.engine import CONNECT_ARGS, build_engine, normalise_database_url
from tests.conftest import TEST_DATABASE_URL


def test_prepared_statements_are_disabled_in_connect_args() -> None:
    """Supabase's transaction-mode pooler cannot carry prepared statements."""
    assert "prepare_threshold" in CONNECT_ARGS
    assert CONNECT_ARGS["prepare_threshold"] is None


def test_engine_is_built_with_those_connect_args() -> None:
    engine = build_engine(TEST_DATABASE_URL)
    try:
        assert engine.pool.__class__ is NullPool
        # SQLAlchemy folds connect_args into the arguments it hands the driver.
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        kwargs.update(CONNECT_ARGS)
        assert kwargs["prepare_threshold"] is None
    finally:
        engine.dispose()


def test_build_engine_does_not_share_the_connect_args_dict() -> None:
    """A caller mutating one engine's args must not affect the next."""
    before = dict(CONNECT_ARGS)
    engine = build_engine(TEST_DATABASE_URL)
    engine.dispose()
    assert CONNECT_ARGS == before


def test_live_connection_has_prepared_statements_disabled(postgres_ready: bool) -> None:
    """Open a real connection and ask psycopg itself.

    This is the assertion that would actually catch a regression: if the
    keyword stopped reaching the driver, ``prepare_threshold`` would be the
    psycopg default of 5 rather than None, and production against the
    transaction pooler would start failing where local development never does.
    """
    if not postgres_ready:
        pytest.skip("Postgres is not reachable; start it with docker compose up -d")

    engine = build_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            driver_connection = connection.connection.driver_connection
            assert driver_connection is not None
            assert driver_connection.prepare_threshold is None
            # and it still works
            assert connection.scalar(text("select 1")) == 1
    finally:
        engine.dispose()


def test_repeated_queries_prepare_nothing_server_side(postgres_ready: bool) -> None:
    """Ask Postgres itself whether anything got prepared on this session.

    psycopg prepares a statement once it has been seen ``prepare_threshold``
    times (default 5), so ten executions would normally leave a row in
    ``pg_prepared_statements``. With preparation disabled the view stays empty,
    which is exactly what the transaction-mode pooler requires.

    ``pg_prepared_statements`` is session-scoped and a documented system view,
    so this asserts the real behaviour without reaching into psycopg internals.
    """
    if not postgres_ready:
        pytest.skip("Postgres is not reachable; start it with docker compose up -d")

    def prepared_count(engine: Engine) -> int:
        with engine.connect() as connection:
            for _ in range(10):
                connection.execute(text("select 1 where 1 = :n"), {"n": 1})
            return connection.scalar(text("select count(*) from pg_prepared_statements")) or 0

    ours = build_engine(TEST_DATABASE_URL)
    try:
        assert prepared_count(ours) == 0
    finally:
        ours.dispose()

    # Control: the same workload on an engine without our connect_args. If this
    # ever stops preparing anything, the assertion above has become vacuous and
    # would no longer catch the setting being dropped.
    control = create_engine(
        normalise_database_url(TEST_DATABASE_URL), poolclass=NullPool, future=True
    )
    try:
        assert prepared_count(control) > 0
    finally:
        control.dispose()


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgres://u:p@h:6543/db?sslmode=require",
            "postgresql+psycopg://u:p@h:6543/db?sslmode=require",
        ),
        (
            "postgresql://u:p@h:6543/db?sslmode=require",
            "postgresql+psycopg://u:p@h:6543/db?sslmode=require",
        ),
        (
            "postgresql+psycopg://u:p@h:6543/db",
            "postgresql+psycopg://u:p@h:6543/db",
        ),
    ],
)
def test_supabase_style_urls_normalise(given: str, expected: str) -> None:
    """A provider string pastes in as-is, query parameters intact."""
    assert normalise_database_url(given) == expected
