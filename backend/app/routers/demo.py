"""Demo reset (FR-15).

Guarded by a shared token. If ``DEMO_RESET_TOKEN`` is not configured the
endpoint behaves as though it does not exist (404) rather than advertising a
disabled feature, so a deployment without the variable has no reset surface at
all (NFR-08).

The reset restores the seed contract and clears change orders. It does NOT
delete audit rows - the log is append-only, so the reset appends a DEMO_RESET
event instead (FR-13).
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.dependencies import RepositoryDep, SettingsDep
from app.domain.audit import SYSTEM_ACTOR, AuditAction, AuditEvent
from app.schemas.demo import DemoResetResponse
from app.seed.demo_contract import DEMO_CONTRACT_ID, build_demo_contracts
from app.seed.presets import PRESETS, SALAMI, build_salami

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset", response_model=DemoResetResponse)
async def reset_demo(
    repo: RepositoryDep,
    settings: SettingsDep,
    x_demo_token: str | None = Header(default=None),
    preset: str | None = Query(
        default=None,
        description="Optional demo preset to apply after restoring the seed.",
    ),
) -> DemoResetResponse:
    """Restore the seed state, optionally applying a demo preset.

    404 when no token is configured, 403 when the supplied token is wrong. A
    preset is built by calling the real service functions with the recorded AI
    outputs, so the state it produces is one the product can actually reach.
    """
    expected = settings.demo_reset_token.strip()
    if not expected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    # Constant-time comparison so a wrong token cannot be probed byte by byte.
    if x_demo_token is None or not secrets.compare_digest(x_demo_token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "BAD_DEMO_TOKEN", "message": "X-Demo-Token is missing or wrong"},
        )

    if preset is not None and preset not in PRESETS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNKNOWN_PRESET",
                "message": f"no demo preset named {preset}; known presets: {', '.join(PRESETS)}",
            },
        )

    repo.reset()
    now = datetime.now(UTC)
    detail: dict[str, object] = {}
    if preset == SALAMI:
        detail = build_salami(repo, now)
    # One event per contract: both baselines were restored.
    for contract in build_demo_contracts():
        repo.append_audit(
            AuditEvent(
                occurred_at=now,
                actor_role=SYSTEM_ACTOR,
                action=AuditAction.DEMO_RESET,
                entity_type="contract",
                entity_id=contract.id,
                contract_id=contract.id,
                reason="demo reset",
            )
        )
    return DemoResetResponse(
        contract_id=DEMO_CONTRACT_ID,
        reset_at=now,
        audit_events_preserved=len(repo.list_audit(DEMO_CONTRACT_ID)),
        preset=preset,
        preset_detail=detail,
    )
