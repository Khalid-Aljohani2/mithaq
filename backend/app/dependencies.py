"""FastAPI dependency providers.

The repository is injected rather than imported directly, so Step 3 can swap the
in-memory store for Postgres without touching a router (NFR-07, NFR-11).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.regulations.loader import Limits, get_limits
from app.repositories.base import ContractRepository
from app.repositories.memory import InMemoryContractRepository


@lru_cache(maxsize=1)
def _repository_singleton() -> InMemoryContractRepository:
    return InMemoryContractRepository()


def get_repository() -> ContractRepository:
    """Return the process-wide repository."""
    return _repository_singleton()


def get_rule_limits() -> Limits:
    """Return the cached, validated limits from the regulation file."""
    return get_limits()


RepositoryDep = Annotated[ContractRepository, Depends(get_repository)]
LimitsDep = Annotated[Limits, Depends(get_rule_limits)]
