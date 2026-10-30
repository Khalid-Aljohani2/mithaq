"""Shared test fixtures.

Database-backed tests run against a dedicated ``mithaq_test`` database so they
never touch local development data. The environment is pointed at it before
application settings are first read, because ``get_settings`` is cached.
"""

import os

import pytest

# Must happen before anything imports app.config: environment variables take
# precedence over the .env file, so this redirects every DB-backed test.
TEST_DATABASE_URL = os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mithaq:mithaq_local_dev@localhost:5433/mithaq_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEMO_RESET_TOKEN"] = "test-demo-token"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"

from collections.abc import Iterator  # noqa: E402

from sqlalchemy import create_engine, text  # noqa: E402

from app.db.engine import normalise_database_url  # noqa: E402
from app.db.tables import Base  # noqa: E402
from app.dependencies import get_repository  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import reset_rate_limiter  # noqa: E402
from app.repositories.base import ContractRepository  # noqa: E402
from app.repositories.memory import InMemoryContractRepository  # noqa: E402
from app.repositories.postgres import PostgresContractRepository  # noqa: E402

DEMO_TOKEN = os.environ["DEMO_RESET_TOKEN"]


def _maintenance_url(url: str) -> str:
    """Point a URL at the server's default database instead of the test one."""
    base, _, _ = normalise_database_url(url).rpartition("/")
    return f"{base}/postgres"


def _ensure_test_database() -> bool:
    """Create the test database and schema. Returns False if Postgres is down."""
    url = normalise_database_url(TEST_DATABASE_URL)
    name = url.rsplit("/", 1)[-1]
    try:
        admin = create_engine(_maintenance_url(url), isolation_level="AUTOCOMMIT")
        with admin.connect() as connection:
            exists = connection.scalar(
                text("select 1 from pg_database where datname = :n"), {"n": name}
            )
            if not exists:
                connection.execute(text(f'create database "{name}"'))
        admin.dispose()
    except Exception:
        return False

    # The whole schema is dropped, not just the tables SQLAlchemy knows about:
    # create_all only adds missing tables, and metadata.drop_all cannot remove a
    # table that has since left the models but still holds a foreign key. Either
    # would leave the test database on an old shape and fail in a way that looks
    # like an application bug. This is a dedicated test database, so starting
    # from empty every session is the honest thing to do.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade"))
        connection.execute(text("create schema public"))
    Base.metadata.create_all(engine)
    engine.dispose()
    return True


@pytest.fixture(scope="session")
def postgres_ready() -> bool:
    """True when a Postgres test database is reachable and migrated."""
    return _ensure_test_database()


def truncate_all() -> None:
    """Empty every table, including the audit log.

    Only tests do this. The application has no truncate or delete path for
    ``audit_log`` anywhere (FR-13).
    """
    engine = create_engine(normalise_database_url(TEST_DATABASE_URL))
    with engine.begin() as connection:
        tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        connection.execute(text(f"truncate table {tables} restart identity cascade"))
    engine.dispose()


@pytest.fixture(params=["memory", "postgres"])
def repository(
    request: pytest.FixtureRequest, postgres_ready: bool
) -> Iterator[ContractRepository]:
    """A clean, seeded repository - once in memory, once in Postgres.

    Every test using this fixture runs twice. That is the point of the
    repository interface: both stores must behave identically (NFR-07).
    """
    repo: ContractRepository
    if request.param == "postgres":
        if not postgres_ready:
            pytest.skip("Postgres is not reachable; start it with docker compose up -d")
        truncate_all()
        repo = PostgresContractRepository()
        repo.reset()
    else:
        repo = InMemoryContractRepository()
    yield repo


@pytest.fixture(autouse=True)
def _fresh_rate_limiter() -> Iterator[None]:
    """Each test gets the full AI rate-limit budget.

    Without this the suite shares one client IP and trips its own limiter
    partway through, which looks like a workflow failure and is not one.
    """
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.fixture
def backend(repository: ContractRepository) -> Iterator[ContractRepository]:
    """Point the FastAPI app at the fixture repository for the whole test.

    Not autouse: pure tests (the rules engine, health) must not be dragged
    through two database backends. API modules opt in with
    ``pytestmark = pytest.mark.usefixtures("backend")``.
    """
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
