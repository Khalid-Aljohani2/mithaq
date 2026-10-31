"""Mithaq FastAPI application entrypoint."""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.config import get_settings
from app.errors import CONTRACT_INTAKE_PATHS, contract_invalid_detail
from app.logging_config import configure_logging
from app.rate_limit import AIRateLimitMiddleware
from app.routers import (
    change_requests,
    contracts,
    demo,
    evaluation,
    health,
    notifications,
    policy,
)

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


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> Response:
    """Give the contract intake routes their ``CONTRACT_INVALID`` shape.

    Every other route keeps FastAPI's default 422 body unchanged.
    """
    if request.method == "POST" and request.url.path.rstrip("/") in CONTRACT_INTAKE_PATHS:
        return JSONResponse(
            status_code=422, content={"detail": contract_invalid_detail(exc.errors())}
        )
    return await request_validation_exception_handler(request, exc)


app.include_router(health.router)
app.include_router(contracts.router)
app.include_router(change_requests.contracts_router)
app.include_router(change_requests.requests_router)
app.include_router(change_requests.vo_router)
app.include_router(notifications.router)
app.include_router(policy.router)
app.include_router(evaluation.router)
app.include_router(demo.router)
