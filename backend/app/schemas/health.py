"""Schemas for the health endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str = Field(description="Service liveness marker.", examples=["ok"])
