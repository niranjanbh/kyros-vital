from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.admin.routes import admin_router
from app.config import settings
from app.core.audit import AuditMiddleware
from app.core.exceptions import AppError, app_error_handler, generic_error_handler
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.shared.routes import health_router, users_router
from app.wellness.routes import (
    lab_reports_router,
    logs_router,
    measurements_router,
    reminders_router,
    tracked_items_router,
)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Kyros Backend",
        version="0.1.0",
        description="Wellness (Phase 1) + Clinic (Phase 2)",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_tags=[
            {"name": "Health", "description": "Service health and readiness."},
            {"name": "Users", "description": "User identity and guest onboarding."},
            {"name": "Wellness", "description": "Phase 1 wellness tracking."},
            {"name": "Clinic", "description": "Phase 2 clinic platform."},
        ],
    )

    app.state.limiter = limiter

    # Starlette stacks middleware LIFO — last added = outermost = first to execute.
    # Target execution order: request_id → CORS → audit → rate_limit → route
    app.add_middleware(SlowAPIMiddleware)  # innermost: rate-limit gate
    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)  # outermost: stamps request_id first

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)

    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(tracked_items_router)
    app.include_router(reminders_router)
    app.include_router(logs_router)
    app.include_router(measurements_router)
    app.include_router(lab_reports_router)

    # Admin panel — mounted after JSON API routes; static files first
    _admin_static = Path(__file__).parent / "admin" / "static"
    app.mount("/admin/static", StaticFiles(directory=str(_admin_static)), name="admin_static")
    app.include_router(admin_router)

    _patch_openapi(app)
    return app


def _patch_openapi(app: FastAPI) -> None:
    """Inject X-Device-Id as a documented header on every operation."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema: dict[str, Any] = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description or "",
            routes=app.routes,
            tags=app.openapi_tags,
        )

        device_id_param: dict[str, Any] = {
            "name": "X-Device-Id",
            "in": "header",
            "required": True,
            "description": "16–64 char alphanumeric+dash device identifier for guest auth.",
            "schema": {"type": "string", "pattern": "^[a-zA-Z0-9\\-]{16,64}$"},
        }
        for path_data in schema.get("paths", {}).values():
            for operation in path_data.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation.setdefault("parameters", []).append(device_id_param)

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


app = create_app()
