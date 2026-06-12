from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.app.database import engine, Base
from backend.app.routes import auth, calculator, habits, challenges, analytics
from backend.app.config import settings
from backend.app.limiter import limiter
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
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
    l = logging.getLogger(logger_name)
    l.handlers = []
    l.propagate = True

logger = logging.getLogger("carbify_backend")
logger.info("Initializing database tables and startup events...")

# Initialize database tables synchronously before accepting traffic
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.database import SessionLocal
    from backend.app.routes.challenges import seed_challenges

    with SessionLocal() as db:
        seed_challenges(db)
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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
async def add_security_headers(request: Request, call_next):
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
app.include_router(auth.router,       prefix="/api")
app.include_router(calculator.router, prefix="/api")
app.include_router(habits.router,     prefix="/api")
app.include_router(challenges.router, prefix="/api")
app.include_router(analytics.router,  prefix="/api")


# ---------------------------------------------------------------------------
# Root & health endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Infrastructure"])
def health_check():
    """
    Lightweight liveness probe consumed by the Docker healthcheck stanza and
    container orchestration platforms (e.g. Kubernetes readiness probe).

    Returns HTTP 200 with ``{"status": "healthy"}`` as long as the application
    process is running and the event loop is responsive.
    """
    return JSONResponse(content={"status": "healthy"}, status_code=200)
