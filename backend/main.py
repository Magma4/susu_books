"""
Susu Books - FastAPI Application Entry Point
Offline, voice-first AI business copilot for informal economy workers.
"""

from collections import defaultdict, deque
import logging
import sys
from time import monotonic
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from database import AsyncSessionLocal, create_tables
from routers import ai, exports, inventory, reports, transactions
from services.inventory_service import InventoryService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("susu_books")

settings = get_settings()

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before serving, and cleanup on shutdown."""
    logger.info("Starting Susu Books backend v%s", settings.app_version)
    await create_tables()
    async with AsyncSessionLocal() as session:
        inventory_service = InventoryService(session)
        await inventory_service.rebuild_from_transactions()
        await session.commit()
    logger.info("AI Provider: Ollama (Local)")
    logger.info("Ollama endpoint: %s", settings.ollama_base_url)
    logger.info("Target model: %s", settings.ollama_model)
    yield
    logger.info("Susu Books backend shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    docs_enabled = settings.api_docs_enabled
    rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Offline, voice-first AI business copilot for informal economy workers. "
            "Powered by Gemma 4."
        ),
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts or ["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        response = await call_next(request)

        if settings.security_headers_enabled:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault(
                "Permissions-Policy",
                "camera=(self), microphone=(self), geolocation=(), interest-cohort=()",
            )
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            if settings.environment == "production":
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )

        response.headers.setdefault("X-Request-ID", request_id)
        return response

    @app.middleware("http")
    async def ai_rate_limit_middleware(request: Request, call_next):
        if request.method == "POST" and request.url.path in {"/api/chat", "/api/chat/image"}:
            client_host = request.client.host if request.client else "unknown"
            now = monotonic()
            bucket = rate_limit_buckets[client_host]
            window = settings.chat_rate_limit_window_seconds

            while bucket and now - bucket[0] > window:
                bucket.popleft()

            if len(bucket) >= settings.chat_rate_limit_requests:
                retry_after = max(1, int(window - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited",
                        "detail": "Too many AI requests. Please wait a moment and try again.",
                        "status_code": 429,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(settings.chat_rate_limit_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            bucket.append(now)
            response = await call_next(request)
            remaining = max(0, settings.chat_rate_limit_requests - len(bucket))
            response.headers.setdefault("X-RateLimit-Limit", str(settings.chat_rate_limit_requests))
            response.headers.setdefault("X-RateLimit-Remaining", str(remaining))
            return response

        return await call_next(request)

    # ------------------------------------------------------------------
    # HTTP exception handler
    # ------------------------------------------------------------------
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "detail": detail,
                "status_code": exc.status_code,
            },
        )

    # ------------------------------------------------------------------
    # Validation exception handler
    # ------------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": "Request validation failed.",
                "status_code": 422,
                "issues": exc.errors(),
            },
        )

    # ------------------------------------------------------------------
    # Global exception handler
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An internal error occurred. Check server logs.",
                "status_code": 500,
            },
        )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(ai.router)
    app.include_router(transactions.router)
    app.include_router(inventory.router)
    app.include_router(reports.router)
    app.include_router(exports.router)

    # ------------------------------------------------------------------
    # Root endpoint
    # ------------------------------------------------------------------
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "environment": settings.environment,
            "docs": "/docs" if docs_enabled else None,
        }

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Run directly (development)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
