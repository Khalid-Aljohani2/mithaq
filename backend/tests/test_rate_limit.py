"""Rate limiting on the AI endpoints (NFR-08)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import FixedWindowLimiter, is_rate_limited_path, reset_rate_limiter
from app.seed.demo_contract import PRIVATE_CONTRACT_ID

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

PRIVATE = f"/api/contracts/{PRIVATE_CONTRACT_ID}"


# ---------------------------------------------------------------------------
# The limiter itself
# ---------------------------------------------------------------------------


def test_limiter_allows_up_to_the_limit_then_refuses() -> None:
    limiter = FixedWindowLimiter(limit=3, window_seconds=60)
    assert [limiter.check("ip", now=0.0)[0] for _ in range(3)] == [True, True, True]
    allowed, remaining, retry_after = limiter.check("ip", now=0.0)
    assert allowed is False
    assert remaining == 0
    assert retry_after == pytest.approx(60.0)


def test_limiter_counts_each_client_separately() -> None:
    limiter = FixedWindowLimiter(limit=1, window_seconds=60)
    assert limiter.check("a", now=0.0)[0] is True
    assert limiter.check("b", now=0.0)[0] is True
    assert limiter.check("a", now=0.0)[0] is False


def test_the_window_rolls_forward() -> None:
    limiter = FixedWindowLimiter(limit=1, window_seconds=60)
    assert limiter.check("ip", now=0.0)[0] is True
    assert limiter.check("ip", now=30.0)[0] is False
    assert limiter.check("ip", now=61.0)[0] is True


def test_remaining_counts_down() -> None:
    limiter = FixedWindowLimiter(limit=3, window_seconds=60)
    assert [limiter.check("ip", now=0.0)[1] for _ in range(3)] == [2, 1, 0]


# ---------------------------------------------------------------------------
# Which paths it covers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "limited"),
    [
        ("/api/change-requests/CR-1/analyse", True),
        ("/api/change-requests/CR-1/variation-order", True),
        ("/api/contracts/CT-1/ledger", False),
        ("/api/contracts/CT-1/change-requests", False),
        ("/api/health", False),
        ("/api/notifications", False),
        ("/docs", False),
    ],
)
def test_only_the_model_spending_endpoints_are_limited(path: str, limited: bool) -> None:
    """Reads must not be throttled; the limit exists to protect credits."""
    assert is_rate_limited_path(path) is limited


# ---------------------------------------------------------------------------
# Over HTTP
# ---------------------------------------------------------------------------


def test_analyse_is_throttled_after_the_limit() -> None:
    """The middleware captured settings at construction, so this drives the
    configured limit rather than patching it: the default is 20 per 60s."""
    reset_rate_limiter()
    codes = [
        client.post("/api/change-requests/CR-A-INSCOPE/analyse").status_code for _ in range(25)
    ]
    assert 429 in codes, "the limiter never engaged"
    first_429 = codes.index(429)
    assert first_429 == 20, f"expected the 21st call to be refused, got {first_429 + 1}"


def test_a_throttled_response_says_how_long_to_wait() -> None:
    reset_rate_limiter()
    for _ in range(21):
        response = client.post("/api/change-requests/CR-A-INSCOPE/analyse")
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) >= 1


def test_allowed_responses_carry_the_remaining_budget() -> None:
    reset_rate_limiter()
    response = client.post("/api/change-requests/CR-A-INSCOPE/analyse")
    assert response.headers["X-RateLimit-Limit"] == "20"
    assert response.headers["X-RateLimit-Remaining"] == "19"


def test_reads_are_never_throttled() -> None:
    reset_rate_limiter()
    for _ in range(30):
        assert client.get(f"{PRIVATE}/ledger").status_code == 200


def test_a_different_client_ip_has_its_own_budget() -> None:
    reset_rate_limiter()
    for _ in range(21):
        client.post("/api/change-requests/CR-A-INSCOPE/analyse")
    other = client.post(
        "/api/change-requests/CR-B-PCR/analyse", headers={"X-Forwarded-For": "203.0.113.9"}
    )
    assert other.status_code != 429
