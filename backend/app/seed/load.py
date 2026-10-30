"""Idempotent seed loader.

    python -m app.seed.load

Inserts the demo contract if it is not already there. Running it twice is safe
and changes nothing the second time, so it can sit in a deploy step.
"""

import sys

from app.config import get_settings
from app.repositories.postgres import seed_contract
from app.seed.demo_contract import build_demo_contract


def main() -> int:
    """Load the demo contract. Returns a process exit code."""
    settings = get_settings()
    if not settings.uses_database:
        sys.stderr.write("DATABASE_URL is not set; nothing to seed.\n")
        return 1

    contract = build_demo_contract()
    inserted = seed_contract(contract)
    if inserted:
        sys.stdout.write(
            f"seeded contract {contract.id} "
            f"({contract.original_value} SAR, {len(contract.items)} items)\n"
        )
    else:
        sys.stdout.write(f"contract {contract.id} already present; nothing to do\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
