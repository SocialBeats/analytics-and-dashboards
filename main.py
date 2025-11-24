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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    try:
        await database.connect()
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    yield
    logger.info("Shutting down application")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(dashboards.router, prefix="/api/v1", tags=["dashboards"])  
app.include_router(widgets.router, prefix="/api/v1", tags=["widgets"])
app.include_router(beat_metrics.router, prefix="/api/v1", tags=["beat_metrics"])


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
