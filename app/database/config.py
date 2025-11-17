"""
MongoDB database configuration and connection management
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.core.config import settings
from app.core.logging import logger


class Database:
    """MongoDB database manager with connection lifecycle"""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """
        Establish connection to MongoDB

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")

            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_CONNECTIONS,
                minPoolSize=settings.MONGODB_MIN_CONNECTIONS,
                serverSelectionTimeoutMS=5000,
            )

            # Verify connection
            await self.client.admin.command("ping")

            self.db = self.client[settings.MONGODB_DB_NAME]

            logger.info(f"Successfully connected to MongoDB database: {settings.MONGODB_DB_NAME}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client is not None:
            logger.info("Closing MongoDB connection")
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed")

    async def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance

        Returns:
            AsyncIOMotorDatabase: The database instance

        Raises:
            RuntimeError: If database is not connected
        """
        if self.db is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self.db


# Global database instance
database = Database()


async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance

    Returns:
        AsyncIOMotorDatabase: The database instance
    """
    return await database.get_database()
