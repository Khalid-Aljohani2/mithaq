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
