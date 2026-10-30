"""FastAPI dependency providers.

The repository is injected rather than imported directly, so the Postgres and
in-memory stores are interchangeable (NFR-07, NFR-11). Which one is used
depends only on whether ``DATABASE_URL`` is set:

* set   -> Postgres. The only correct choice on Vercel, where a function keeps
           no memory between requests.
* unset -> in-memory. Fine for unit tests and a quick local run; state is lost
           whenever the process restarts.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.regulations.loader import Limits, get_limits
from app.repositories.base import ContractRepository
from app.repositories.memory import InMemoryContractRepository


@lru_cache(maxsize=1)
def _repository_singleton() -> ContractRepository:
    settings = get_settings()
    if settings.uses_database:
        from app.repositories.postgres import PostgresContractRepository

        return PostgresContractRepository()
    return InMemoryContractRepository()


def get_repository() -> ContractRepository:
    """Return the process-wide repository."""
    return _repository_singleton()


def reset_repository_cache() -> None:
    """Drop the cached repository so the next call re-reads settings.

    Used by tests that switch between the in-memory and Postgres stores.
    """
    _repository_singleton.cache_clear()


def get_rule_limits() -> Limits:
    """Return the cached, validated limits from the regulation file."""
    return get_limits()


RepositoryDep = Annotated[ContractRepository, Depends(get_repository)]
LimitsDep = Annotated[Limits, Depends(get_rule_limits)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
