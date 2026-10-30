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

from app.analysis.fallback import build_provider
from app.analysis.provider import AnalysisProvider
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


@lru_cache(maxsize=1)
def _provider_singleton() -> AnalysisProvider:
    """The analysis provider, chosen from settings.

    LLM_PROVIDER=anthropic with a key gives the live provider behind a
    recorded-output fallback (FR-19); anything else gives the scripted
    provider, which is what lets the whole suite and the demo run with no key.
    """
    return build_provider(get_settings())


def reset_provider_cache() -> None:
    """Drop the cached provider so the next call re-reads settings."""
    _provider_singleton.cache_clear()


def get_provider() -> AnalysisProvider:
    """Return the process-wide analysis provider."""
    return _provider_singleton()


def get_rule_limits() -> Limits:
    """Return the cached, validated limits from the regulation file."""
    return get_limits()


RepositoryDep = Annotated[ContractRepository, Depends(get_repository)]
LimitsDep = Annotated[Limits, Depends(get_rule_limits)]
ProviderDep = Annotated[AnalysisProvider, Depends(get_provider)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
