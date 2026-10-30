"""Notification routes (FR-11)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.dependencies import RepositoryDep
from app.domain.enums import Party, Role
from app.schemas.change_requests import NotificationListResponse
from app.services import change_requests as svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    repo: RepositoryDep,
    party: Party = Query(description="Which side of the contract."),
    role: Role = Query(description="Which role's inbox."),
) -> NotificationListResponse:
    """Notifications for one role, with reminders computed on the fly.

    There is no background job: a reminder for an approval that has been
    pending too long is derived at read time, so nothing has to be running for
    it to appear.
    """
    now = datetime.now(UTC)
    reminders = svc.reminders_for(repo, party, role, now)
    stored = repo.list_notifications(party, role)
    return NotificationListResponse(
        party=party,
        role=role,
        notifications=[*reminders, *stored],
        reminder_count=len(reminders),
    )
