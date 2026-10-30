"""Response models for the demo endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DemoResetResponse(BaseModel):
    """Confirmation that the seed state was restored (FR-15)."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    reset_at: datetime
    #: Audit rows are never deleted, so this only ever grows.
    audit_events_preserved: int
    #: Which preset was applied after the seed was restored, if any.
    preset: str | None = None
    #: What the preset built, so a demo script can name the requests it needs
    #: without guessing ids.
    preset_detail: dict[str, object] = {}
