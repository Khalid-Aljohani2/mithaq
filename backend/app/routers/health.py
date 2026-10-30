"""Health check routes."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def read_health() -> HealthResponse:
    """Report that the API is up."""
    return HealthResponse(status="ok")
