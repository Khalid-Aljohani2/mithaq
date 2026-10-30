"""Policy routes: what the organisation requires, as configuration says it.

Everything here is read from ``policy.yaml`` and the stage 2 checklist. Nothing
is written out a second time in Python, so the UI and the pipeline cannot drift
apart on what a request needs (NFR-16).
"""

from fastapi import APIRouter

from app.pipeline.documents import CHECKLISTS
from app.policy.loader import get_policy
from app.schemas.policy import (
    DocumentChecklist,
    PolicyThresholdOut,
    RequiredDocumentsResponse,
)

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.get("/required-documents", response_model=RequiredDocumentsResponse)
async def required_documents() -> RequiredDocumentsResponse:
    """The stage 2 checklist, keyed by impact type (FR-04).

    The UI uses this to show a requester what a cost-bearing request will need
    *before* they submit it, rather than after stage 2 sends it back. It is the
    same table stage 2 compares against, read from the same place.
    """
    return RequiredDocumentsResponse(
        checklists=[
            DocumentChecklist(impact_type=impact, required=list(documents))
            for impact, documents in CHECKLISTS.items()
        ]
    )


@router.get("/thresholds", response_model=list[PolicyThresholdOut])
async def thresholds() -> list[PolicyThresholdOut]:
    """Every configured threshold with the source that justifies it (NFR-16)."""
    return [
        PolicyThresholdOut(
            key=key,
            source=threshold.source,
            cap_pct=threshold.cap_pct,
            cap_value=threshold.cap_value,
            basis=threshold.basis,
            blocking=threshold.blocking,
            exception_role=threshold.exception_role,
            description_ar=threshold.description_ar,
            description_en=threshold.description_en,
        )
        for key, threshold in get_policy().thresholds.items()
    ]
