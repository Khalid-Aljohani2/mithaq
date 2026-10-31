"""Local demo mode: a token-free reset, for loopback clients only.

Both sides of the guard are pinned here. Demo mode must open the reset to
this machine and to nothing else; with it off, the token rules are unchanged.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from tests.conftest import DEMO_TOKEN

pytestmark = pytest.mark.usefixtures("backend")

LOCAL = TestClient(app, client=("127.0.0.1", 50000))
LOCAL_V6 = TestClient(app, client=("::1", 50000))
REMOTE = TestClient(app, client=("203.0.113.7", 50000))


@pytest.fixture
def settings_override() -> Iterator[Any]:
    """Install a Settings instance for one test; ``backend`` clears it after."""

    def install(**values: Any) -> None:
        settings = Settings(**values)
        app.dependency_overrides[get_settings] = lambda: settings

    yield install
    app.dependency_overrides.pop(get_settings, None)


# ---------------------------------------------------------------------------
# Demo mode on
# ---------------------------------------------------------------------------


def test_demo_mode_localhost_resets_without_token(settings_override: Any) -> None:
    settings_override(demo_mode=True)

    response = LOCAL.post("/api/demo/reset")

    assert response.status_code == 200
    assert response.json()["preset"] is None


def test_demo_mode_localhost_applies_preset_without_token(settings_override: Any) -> None:
    settings_override(demo_mode=True)

    response = LOCAL.post("/api/demo/reset?preset=salami")

    assert response.status_code == 200
    assert response.json()["preset"] == "salami"


def test_demo_mode_ipv6_loopback_resets_without_token(settings_override: Any) -> None:
    settings_override(demo_mode=True)

    assert LOCAL_V6.post("/api/demo/reset").status_code == 200


def test_demo_mode_localhost_works_even_with_no_token_configured(
    settings_override: Any,
) -> None:
    settings_override(demo_mode=True, demo_reset_token="")

    assert LOCAL.post("/api/demo/reset").status_code == 200


def test_demo_mode_remote_client_without_token_is_refused(settings_override: Any) -> None:
    settings_override(demo_mode=True)

    assert REMOTE.post("/api/demo/reset").status_code == 403
    assert REMOTE.post("/api/demo/reset?preset=salami").status_code == 403


def test_demo_mode_remote_client_with_no_token_configured_gets_404(
    settings_override: Any,
) -> None:
    settings_override(demo_mode=True, demo_reset_token="")

    assert REMOTE.post("/api/demo/reset").status_code == 404


def test_demo_mode_remote_client_with_correct_token_still_works(
    settings_override: Any,
) -> None:
    settings_override(demo_mode=True)

    response = REMOTE.post("/api/demo/reset", headers={"X-Demo-Token": DEMO_TOKEN})

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Demo mode off: the token rules are unchanged, localhost included
# ---------------------------------------------------------------------------


def test_demo_mode_off_localhost_without_token_is_refused(settings_override: Any) -> None:
    settings_override(demo_mode=False)

    assert LOCAL.post("/api/demo/reset").status_code == 403
    assert LOCAL.post("/api/demo/reset?preset=salami").status_code == 403


def test_demo_mode_off_localhost_with_no_token_configured_gets_404(
    settings_override: Any,
) -> None:
    settings_override(demo_mode=False, demo_reset_token="")

    assert LOCAL.post("/api/demo/reset").status_code == 404


def test_demo_mode_off_localhost_with_token_works(settings_override: Any) -> None:
    settings_override(demo_mode=False)

    response = LOCAL.post("/api/demo/reset", headers={"X-Demo-Token": DEMO_TOKEN})

    assert response.status_code == 200


def test_demo_mode_is_off_by_default() -> None:
    assert Settings.model_fields["demo_mode"].default is False


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("enabled", [True, False])
def test_status_reports_demo_mode(settings_override: Any, enabled: bool) -> None:
    settings_override(demo_mode=enabled)

    response = REMOTE.get("/api/demo/status")

    assert response.status_code == 200
    assert response.json() == {"demo_mode": enabled}


def test_status_does_not_reveal_the_token(settings_override: Any) -> None:
    settings_override(demo_mode=True)

    body = REMOTE.get("/api/demo/status").text

    assert DEMO_TOKEN not in body
    assert "token" not in body.lower()
