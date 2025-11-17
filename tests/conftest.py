"""
Pytest configuration and fixtures
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from main import app
from app.core.config import settings
from app.database import database


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for async tests"""
    return "asyncio"


@pytest_asyncio.fixture
async def test_db():
    """Create a test database instance"""
    test_db_name = f"{settings.MONGODB_DB_NAME}_test"
    test_client = AsyncIOMotorClient(settings.MONGODB_URL)
    test_database = test_client[test_db_name]

    yield test_database

    # Cleanup: drop test database
    await test_client.drop_database(test_db_name)
    test_client.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_item_data():
    """Sample item data for testing"""
    return {
        "title": "Test Item",
        "description": "This is a test item",
        "completed": False
    }
