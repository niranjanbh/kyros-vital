from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.audit import AuditMiddleware
from app.core.exceptions import AppError, app_error_handler, generic_error_handler
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.shared.routes import health_router, users_router


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

    # Attach limiter to app state (required by slowapi)
    app.state.limiter = limiter

    # Middleware — order matters: first added = outermost wrapper
    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)

    # Routers
    app.include_router(health_router)
    app.include_router(users_router)

    # Wellness and clinic routers are mounted in P4/P5

    return app


app = create_app()
