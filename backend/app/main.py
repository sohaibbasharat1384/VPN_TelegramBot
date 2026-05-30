"""FastAPI application factory and entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.logging import configure_logging, get_logger

logger = get_logger("app")

_STATUS_FOR_ERROR: dict[type[DomainError], int] = {
    NotFoundError: 404,
    PermissionDeniedError: 403,
    ValidationError: 422,
    ConflictError: 409,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", environment=settings.environment, app=settings.app_name)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        status = next(
            (s for cls, s in _STATUS_FOR_ERROR.items() if isinstance(exc, cls)), 400
        )
        return JSONResponse(
            status_code=status,
            content={"error": {"code": exc.code, "message": exc.user_message}},
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    # Versioned API router (auth, users, payments, … added in later increments).
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
