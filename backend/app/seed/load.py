"""Idempotent seed loader.

    python -m app.seed.load

Inserts the demo contracts and change requests if they are not already there.
Running it twice is safe and changes nothing the second time, so it can sit in
a deploy step.
"""

import sys

from app.config import get_settings
from app.repositories.postgres import seed_all


def main() -> int:
    """Load the demo data. Returns a process exit code."""
    settings = get_settings()
    if not settings.uses_database:
        sys.stderr.write("DATABASE_URL is not set; nothing to seed.\n")
        return 1

    inserted = seed_all()
    if any(inserted.values()):
        sys.stdout.write(
            f"seeded {inserted['contracts']} contract(s), "
            f"repaired {inserted['repaired']} contract(s), "
            f"seeded {inserted['change_requests']} change request(s)\n"
        )
    else:
        sys.stdout.write("demo data already present and whole; nothing to do\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
