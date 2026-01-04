from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.config import get_db
from app.services.kafka_consumer import kafka_service

router = APIRouter()


@router.get("/analytics/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Health check endpoint
    """
    try:
        # Try to execute a simple command to check MongoDB connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}


@router.get("/kafka/health")
async def kafka_health_check():
    """
    Kafka health check endpoint
    Verifies whether Kafka is currently reachable and responding
    """
    health_status = await kafka_service.check_health()

    if health_status["kafka"] == "connected":
        return health_status
    else:
        from fastapi import status
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_status)
