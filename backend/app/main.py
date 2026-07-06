"""backend/app/main.py
─────────────────────────────────────────────────────────────
Application entry point for the Carbifyio FastAPI backend.

Responsibilities:
  • Configure structured JSON logging for all application loggers.
  • Create database tables (synchronous, before traffic).
  • Register lifespan hooks (seed challenges & habits on startup).
  • Mount CORS, rate-limiting, and security-header middleware.
  • Include all API routers under the ``/api`` prefix.
  • Expose root (``/``) and health-check (``/health``) endpoints.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
import json
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import Response

from backend.app.config import settings
from backend.app.database import Base, engine
from backend.app.limiter import limiter
from backend.app.routes import analytics, auth, calculator, challenges, habits

# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize *record* into a compact JSON string.

        Fields emitted: ``timestamp``, ``level``, ``logger``, ``message``,
        and (when present) ``exception``.
        """
        log_data: dict[str, str] = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


# Setup root handler with JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]

# Propagate Uvicorn and FastAPI logs to root to enforce JSON formatting
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
    _logger = logging.getLogger(logger_name)
    _logger.handlers = []
    _logger.propagate = True

logger = logging.getLogger("carbify_backend")
logger.info("Initializing database tables and startup events...")

# Initialize database tables synchronously before accepting traffic
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Seed default challenges and habits on application startup."""
    from backend.app.database import SessionLocal
    from backend.app.routes.challenges import seed_challenges
    from backend.app.routes.habits import seed_habits

    with SessionLocal() as db:
        Base.metadata.create_all(bind=db.get_bind())
        seed_challenges(db)
        seed_habits(db)
    yield


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend service for Carbon Footprint Awareness Platform (Carbifyio)",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS — explicit allowlists, no wildcards
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    # Explicit method list — avoids overly-permissive wildcard CORS
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # Explicit header list — avoids overly-permissive wildcard CORS
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ---------------------------------------------------------------------------
# Security headers middleware (Helmet equivalents for FastAPI)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Inject hardened HTTP security headers into every response.

    Headers set:
      • ``X-Frame-Options: DENY`` — prevents clickjacking.
      • ``X-Content-Type-Options: nosniff`` — prevents MIME sniffing.
      • ``X-XSS-Protection: 1; mode=block`` — XSS mitigation.
      • ``Referrer-Policy`` — limits referrer leakage.
      • ``Permissions-Policy`` — restricts device API access.
      • ``Content-Security-Policy`` — allowlists trusted sources.
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # connect-src uses 'self' — all API traffic is proxied via Nginx, so the
    # browser never needs to reach backend:8000 directly.  Works in both local
    # dev (via port forward) and container-to-container networking.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "img-src 'self' data:;"
    )
    return response


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api")
app.include_router(calculator.router, prefix="/api")
app.include_router(habits.router, prefix="/api")
app.include_router(challenges.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


# ---------------------------------------------------------------------------
# Root & health endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a minimal JSON envelope confirming the API is reachable."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Infrastructure"])
def health_check() -> JSONResponse:
    """Lightweight liveness probe consumed by the Docker healthcheck stanza and
    container orchestration platforms (e.g. Kubernetes readiness probe).

    Returns HTTP 200 with ``{"status": "healthy"}`` as long as the application
    process is running and the event loop is responsive.
    """
    return JSONResponse(content={"status": "healthy"}, status_code=200)


__all__ = ["app"]
