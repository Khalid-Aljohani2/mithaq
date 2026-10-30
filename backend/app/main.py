"""Mithaq FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.rate_limit import AIRateLimitMiddleware
from app.routers import change_requests, contracts, demo, health, notifications

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name, version=settings.app_version)

# Origins come from the ALLOWED_ORIGINS setting (comma separated), so production
# can allow its own frontend domain without a code change (NFR-08).
# allow_credentials stays False so the wildcard method/header lists remain valid.
# Rate limits the endpoints that can spend model credits (NFR-08).
app.add_middleware(AIRateLimitMiddleware, settings=settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(contracts.router)
app.include_router(change_requests.contracts_router)
app.include_router(change_requests.requests_router)
app.include_router(change_requests.vo_router)
app.include_router(notifications.router)
app.include_router(demo.router)
