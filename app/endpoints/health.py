from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.config import get_db

router = APIRouter()


@router.get("/analytics/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Health check endpoint
    """
    try:
        # Try to execute a simple command to check MongoDB connection
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected"
        }
