"""
FastAPI MongoDB Template - Main Application
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.database import database
from app.endpoints import health
from app.endpoints import dashboards
from app.endpoints import widgets
from app.endpoints import beat_metrics
from app.endpoints.examples import example_rate_limit
from app.middleware.authentication import verify_jwt_token
from app.middleware.rate_limiter import limiter, init_redis, close_redis, rate_limit_handler
from slowapi.errors import RateLimitExceeded
from app.middleware.circuit_breaker import circuit_breaker_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    try:
        await database.connect()
        await init_redis()  # Initialize Redis for rate limiting
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    yield
    logger.info("Shutting down application")
    await close_redis()  # Close Redis connection
    await database.disconnect()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Add rate limiter state to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# JWT Authentication Middleware
app.middleware("http")(verify_jwt_token)
# Circuit Breaker Middleware
app.middleware("http")(circuit_breaker_middleware)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(dashboards.router, prefix="/api/v1", tags=["dashboards"])
app.include_router(widgets.router, prefix="/api/v1", tags=["widgets"])
app.include_router(beat_metrics.router, prefix="/api/v1", tags=["beat_metrics"])
app.include_router(example_rate_limit.router, prefix="/api/v1", tags=["examples_rate_limit"])


@app.get("/", tags=["root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/analytics/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
