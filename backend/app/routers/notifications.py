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

    There is no background job: a reminder for an approval or a document that
    has been waited on too long is derived at read time, so nothing has to be
    running for it to appear.

    Built by ``svc.notifications_for`` rather than assembled here. This route
    used to compose the list itself, which meant the document reminders and
    the dropping of answered asks - both of which live in that function -
    never reached the API at all. One inbox, built in one place.
    """
    items = svc.notifications_for(repo, party, role, datetime.now(UTC))
    return NotificationListResponse(
        party=party,
        role=role,
        notifications=items,
        reminder_count=sum(1 for item in items if item.is_reminder),
    )
