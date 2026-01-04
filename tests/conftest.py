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


# ==================== Dashboard Fixtures ====================


@pytest.fixture
def mock_user_regular():
    """Mock regular user data"""
    return {
        "userId": "user123",
        "username": "testuser",
        "roles": ["user"],
        "email": "test@example.com"
    }


@pytest.fixture
def mock_user_admin():
    """Mock admin user data"""
    return {
        "userId": "admin123",
        "username": "adminuser",
        "roles": ["admin", "user"],
        "email": "admin@example.com"
    }


@pytest.fixture
def sample_dashboard_data():
    """Sample dashboard creation data"""
    return {
        "name": "Test Dashboard",
        "beatId": "beat123"
    }


@pytest.fixture
def sample_dashboard_update_data():
    """Sample dashboard update data"""
    return {
        "name": "Updated Dashboard Name"
    }


@pytest.fixture
def mock_beat_ownership_response():
    """Mock successful beat ownership verification response"""
    return {
        "beatId": "beat123",
        "ownerId": "user123",
        "title": "Test Beat",
        "createdBy": {
            "userId": "user123",
            "username": "testuser"
        }
    }


# ==================== Widget Fixtures ====================


@pytest.fixture
def sample_widget_data():
    """Sample widget creation data"""
    return {
        "dashboardId": "507f191e810c19729de860ea",
        "metricType": "BPM"
    }


@pytest.fixture
def sample_widget_update_data():
    """Sample widget update data"""
    return {
        "metricType": "ENERGY"
    }


@pytest.fixture
def mock_dashboard_doc():
    """Mock dashboard document for widget tests"""
    from bson import ObjectId
    return {
        "_id": ObjectId("507f191e810c19729de860ea"),
        "owner_id": "user123",
        "beat_id": "beat123",
        "name": "Test Dashboard",
        "created_at": __import__('datetime').datetime.utcnow(),
        "updated_at": None
    }


# ==================== Beat Metrics Fixtures ====================


@pytest.fixture
def sample_core_metrics():
    """Sample core metrics data"""
    return {
        "energy": 0.83,
        "dynamism": 0.61,
        "percussiveness": 0.74,
        "brigthness": 0.56,
        "density": 7.2,
        "richness": 0.68
    }


@pytest.fixture
def sample_extra_metrics():
    """Sample extra metrics data"""
    return {
        "bpm": 122.5,
        "num_beats": 245,
        "mean_duration": 0.489,
        "beats_position": 0.75,
        "key": "Am",
        "uniformity": 0.81,
        "stability": 0.76,
        "chroma_features": {"C": 0.8, "D": 0.3},
        "decibels": 85.5,
        "hz_range": 440.0,
        "mean_hz": 220.0,
        "character": "smooth",
        "opening": 0.65,
        "style": "legato",
        "suddent_changes": 5.0,
        "soft_changes": 12.0,
        "ratio_sudden_soft": 0.42
    }


@pytest.fixture
def sample_beat_metrics_data(sample_core_metrics, sample_extra_metrics):
    """Sample beat metrics creation data"""
    return {
        "beatId": "beat123",
        "audioUrl": "https://example.com/audio.mp3"
    }


@pytest.fixture
def sample_beat_metrics_update_data(sample_core_metrics):
    """Sample beat metrics update data"""
    return {
        "coreMetrics": sample_core_metrics
    }


@pytest.fixture
def mock_beat_metrics_doc(sample_core_metrics, sample_extra_metrics):
    """Mock beat metrics document"""
    from bson import ObjectId
    import datetime
    return {
        "_id": ObjectId("507f191e810c19729de860eb"),
        "beatId": "beat123",
        "coreMetrics": sample_core_metrics,
        "extraMetrics": sample_extra_metrics,
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": None
    }


@pytest.fixture
def mock_audio_analysis_result(sample_core_metrics, sample_extra_metrics):
    """Mock result from audio analysis"""
    return (sample_core_metrics, sample_extra_metrics)
