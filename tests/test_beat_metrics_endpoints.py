"""
Integration tests for Beat Metrics endpoints
Tests complete API flow with real database operations
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from io import BytesIO
from bson import ObjectId
import datetime

from main import app
from app.database.config import get_db


@pytest_asyncio.fixture
async def db_with_beat_metrics(test_db, sample_core_metrics, sample_extra_metrics):
    """Create a test beat metrics in the database"""
    beat_metrics_doc = {
        "_id": ObjectId(),
        "beatId": "beat123",
        "coreMetrics": sample_core_metrics,
        "extraMetrics": sample_extra_metrics,
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": None,
    }
    result = await test_db.beat_metrics.insert_one(beat_metrics_doc)
    beat_metrics_doc["_id"] = result.inserted_id

    # Serialize for return
    created = {
        "id": str(beat_metrics_doc["_id"]),
        "beatId": beat_metrics_doc["beatId"],
        "coreMetrics": beat_metrics_doc["coreMetrics"],
        "extraMetrics": beat_metrics_doc["extraMetrics"],
        "createdAt": beat_metrics_doc["createdAt"].isoformat() + "Z",
        "updatedAt": beat_metrics_doc["updatedAt"],
    }

    yield test_db, created

    # Cleanup
    await test_db.beat_metrics.delete_many({})


@pytest_asyncio.fixture
async def client_with_test_db(client, test_db):
    """Override the get_db dependency to use test database"""

    async def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    yield client
    app.dependency_overrides.clear()


# ==================== Test List Beat Metrics ====================


class TestListBeatMetrics:
    """Test GET /analytics/beat-metrics endpoint"""

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_list_beat_metrics_success(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test successful retrieval of beat metrics list"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        response = await client_with_test_db.get(
            "/api/v1/analytics/beat-metrics",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(bm["beatId"] == "beat123" for bm in data)

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_list_beat_metrics_filtered_by_beat_id(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test retrieval filtered by beat_id"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        response = await client_with_test_db.get(
            "/api/v1/analytics/beat-metrics?beatId=beat123",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(bm["beatId"] == "beat123" for bm in data)

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_list_beat_metrics_with_pagination(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test retrieval with pagination parameters"""
        mock_auth.return_value = mock_user_regular

        response = await client_with_test_db.get(
            "/api/v1/analytics/beat-metrics?skip=0&limit=10",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_list_beat_metrics_empty(
        self, mock_auth, client_with_test_db, test_db, mock_user_regular
    ):
        """Test retrieval when no beat metrics exist"""
        mock_auth.return_value = mock_user_regular

        # Clean up any existing metrics
        await test_db.beat_metrics.delete_many({})

        response = await client_with_test_db.get(
            "/api/v1/analytics/beat-metrics",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ==================== Test Get Beat Metrics by ID ====================


class TestGetBeatMetrics:
    """Test GET /analytics/beat-metrics/{beat_metrics_id} endpoint"""

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_get_beat_metrics_success(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test successful retrieval of beat metrics by ID"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics
        beat_metrics_id = created["id"]

        response = await client_with_test_db.get(
            f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == beat_metrics_id
        assert data["beatId"] == "beat123"
        assert "coreMetrics" in data
        assert "extraMetrics" in data

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_get_beat_metrics_not_found(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test retrieval of non-existent beat metrics"""
        mock_auth.return_value = mock_user_regular
        fake_id = "507f191e810c19729de860ea"

        response = await client_with_test_db.get(
            f"/api/v1/analytics/beat-metrics/{fake_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_get_beat_metrics_invalid_id(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test retrieval with invalid ObjectId format"""
        mock_auth.return_value = mock_user_regular

        response = await client_with_test_db.get(
            "/api/v1/analytics/beat-metrics/invalid_id",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


# ==================== Test Create Beat Metrics ====================


class TestCreateBeatMetrics:
    """Test POST /analytics/beat-metrics endpoint"""

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_create_beat_metrics_success_with_file(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_core_metrics,
        sample_extra_metrics,
    ):
        """Test successful beat metrics creation with audio file"""
        mock_auth.return_value = mock_user_regular

        with (
            patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify,
            patch("app.services.beat_metrics_service.analyze_audio_file") as mock_analyze,
        ):

            mock_verify.return_value = AsyncMock()
            mock_analyze.return_value = (sample_core_metrics, sample_extra_metrics)

            with patch("app.services.beat_metrics_service.AudioFileHandler") as MockAudioHandler:
                mock_handler = MagicMock()
                mock_handler.save_upload = AsyncMock(return_value="/tmp/test.mp3")
                mock_handler.cleanup = MagicMock()
                MockAudioHandler.return_value = mock_handler

                audio_content = b"fake audio content"
                files = {"audioFile": ("test.mp3", BytesIO(audio_content), "audio/mpeg")}
                data = {"beatId": "beat456"}

                response = await client_with_test_db.post(
                    "/api/v1/analytics/beat-metrics",
                    data=data,
                    files=files,
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": "user123",
                        "x-roles": '["user"]',
                    },
                )

                assert response.status_code == 201
                result = response.json()
                assert result["beatId"] == "beat456"
                assert "coreMetrics" in result
                assert "extraMetrics" in result

                # Cleanup
                await test_db.beat_metrics.delete_one({"beatId": "beat456"})

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_create_beat_metrics_success_with_url(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_core_metrics,
        sample_extra_metrics,
    ):
        """Test successful beat metrics creation with audio URL"""
        mock_auth.return_value = mock_user_regular

        with (
            patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify,
            patch("app.services.beat_metrics_service.analyze_audio_file") as mock_analyze,
        ):

            mock_verify.return_value = AsyncMock()
            mock_analyze.return_value = (sample_core_metrics, sample_extra_metrics)

            with patch("app.services.beat_metrics_service.AudioFileHandler") as MockAudioHandler:
                mock_handler = MagicMock()
                mock_handler.download_from_url = AsyncMock(return_value="/tmp/test.mp3")
                mock_handler.cleanup = MagicMock()
                MockAudioHandler.return_value = mock_handler

                data = {"beatId": "beat789", "audioUrl": "https://example.com/audio.mp3"}

                response = await client_with_test_db.post(
                    "/api/v1/analytics/beat-metrics",
                    data=data,
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": "user123",
                        "x-roles": '["user"]',
                    },
                )

                assert response.status_code == 201
                result = response.json()
                assert result["beatId"] == "beat789"

                # Cleanup
                await test_db.beat_metrics.delete_one({"beatId": "beat789"})

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_create_beat_metrics_admin(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_admin,
        sample_core_metrics,
        sample_extra_metrics,
    ):
        """Test admin can create metrics for any beat"""
        mock_auth.return_value = mock_user_admin

        with (
            patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify,
            patch("app.services.beat_metrics_service.analyze_audio_file") as mock_analyze,
        ):

            mock_verify.return_value = AsyncMock()
            mock_analyze.return_value = (sample_core_metrics, sample_extra_metrics)

            with patch("app.services.beat_metrics_service.AudioFileHandler") as MockAudioHandler:
                mock_handler = MagicMock()
                mock_handler.save_upload = AsyncMock(return_value="/tmp/test.mp3")
                mock_handler.cleanup = MagicMock()
                MockAudioHandler.return_value = mock_handler

                audio_content = b"fake audio content"
                files = {"audioFile": ("test.mp3", BytesIO(audio_content), "audio/mpeg")}
                data = {"beatId": "beat_other_user"}

                response = await client_with_test_db.post(
                    "/api/v1/analytics/beat-metrics",
                    data=data,
                    files=files,
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": "admin123",
                        "x-roles": '["admin", "user"]',
                    },
                )

                assert response.status_code == 201
                result = response.json()
                assert result["beatId"] == "beat_other_user"

                # Cleanup
                await test_db.beat_metrics.delete_one({"beatId": "beat_other_user"})

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_create_beat_metrics_user_doesnt_own_beat(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test creation fails when user doesn't own the beat"""
        mock_auth.return_value = mock_user_regular

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            from app.core.exceptions import BadRequestException

            mock_verify.side_effect = BadRequestException("User doesn't own the beat")

            audio_content = b"fake audio content"
            files = {"audioFile": ("test.mp3", BytesIO(audio_content), "audio/mpeg")}
            data = {"beatId": "beat_not_owned"}

            response = await client_with_test_db.post(
                "/api/v1/analytics/beat-metrics",
                data=data,
                files=files,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 400
            assert "doesn't own" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_create_beat_metrics_no_audio_source(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test creation fails when no audio file or URL provided"""
        mock_auth.return_value = mock_user_regular

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            mock_verify.return_value = AsyncMock()

            data = {"beatId": "beat123"}

            response = await client_with_test_db.post(
                "/api/v1/analytics/beat-metrics",
                data=data,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 400
            assert "audio" in response.json()["detail"].lower()


# ==================== Test Update Beat Metrics ====================


class TestUpdateBeatMetrics:
    """Test PUT /analytics/beat-metrics/{beat_metrics_id} endpoint"""

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_update_beat_metrics_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_beat_metrics,
        mock_user_regular,
        sample_core_metrics,
    ):
        """Test successful beat metrics update"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            mock_verify.return_value = AsyncMock()

            beat_metrics_id = created["id"]
            update_data = {
                "coreMetrics": {
                    "energy": 0.95,
                    "dynamism": 0.75,
                    "percussiveness": 0.85,
                    "brigthness": 0.65,
                    "density": 8.5,
                    "richness": 0.78,
                }
            }

            response = await client_with_test_db.put(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                json=update_data,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == beat_metrics_id
            assert data["coreMetrics"]["energy"] == 0.95

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_update_beat_metrics_user_doesnt_own_beat(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test update fails when user doesn't own the beat"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            from app.core.exceptions import BadRequestException

            mock_verify.side_effect = BadRequestException("User doesn't own the beat")

            beat_metrics_id = created["id"]
            update_data = {
                "coreMetrics": {
                    "energy": 0.95,
                    "dynamism": 0.75,
                    "percussiveness": 0.85,
                    "brigthness": 0.65,
                    "density": 8.5,
                    "richness": 0.78,
                }
            }

            response = await client_with_test_db.put(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                json=update_data,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_update_beat_metrics_admin_can_update_any(
        self,
        mock_auth,
        client_with_test_db,
        db_with_beat_metrics,
        mock_user_admin,
        sample_core_metrics,
    ):
        """Test admin can update any beat metrics"""
        mock_auth.return_value = mock_user_admin
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            mock_verify.return_value = AsyncMock()

            beat_metrics_id = created["id"]
            update_data = {"coreMetrics": sample_core_metrics}

            response = await client_with_test_db.put(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                json=update_data,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "admin123",
                    "x-roles": '["admin", "user"]',
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_update_beat_metrics_not_found(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test update of non-existent beat metrics"""
        mock_auth.return_value = mock_user_regular
        fake_id = "507f191e810c19729de860ea"
        update_data = {
            "coreMetrics": {
                "energy": 0.95,
                "dynamism": 0.75,
                "percussiveness": 0.85,
                "brigthness": 0.65,
                "density": 8.5,
                "richness": 0.78,
            }
        }

        response = await client_with_test_db.put(
            f"/api/v1/analytics/beat-metrics/{fake_id}",
            json=update_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_update_beat_metrics_empty_update(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test update with no changes"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            mock_verify.return_value = AsyncMock()

            beat_metrics_id = created["id"]
            update_data = {}

            response = await client_with_test_db.put(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                json=update_data,
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 200


# ==================== Test Delete Beat Metrics ====================


class TestDeleteBeatMetrics:
    """Test DELETE /analytics/beat-metrics/{beat_metrics_id} endpoint"""

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_delete_beat_metrics_success(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test successful beat metrics deletion"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            mock_verify.return_value = AsyncMock()

            beat_metrics_id = created["id"]

            response = await client_with_test_db.delete(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 200

            # Verify deletion
            verify_response = await client_with_test_db.get(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )
            assert verify_response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_delete_beat_metrics_user_doesnt_own_beat(
        self, mock_auth, client_with_test_db, db_with_beat_metrics, mock_user_regular
    ):
        """Test deletion fails when user doesn't own the beat"""
        mock_auth.return_value = mock_user_regular
        test_db, created = db_with_beat_metrics

        with patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify:
            from app.core.exceptions import BadRequestException

            mock_verify.side_effect = BadRequestException("User doesn't own the beat")

            beat_metrics_id = created["id"]

            response = await client_with_test_db.delete(
                f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": "user123",
                    "x-roles": '["user"]',
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_delete_beat_metrics_admin_can_delete_any(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_admin,
        sample_core_metrics,
        sample_extra_metrics,
    ):
        """Test admin can delete any beat metrics"""
        mock_auth.return_value = mock_user_admin

        # First create a beat metrics
        with (
            patch("app.services.beat_metrics_service.verify_beat_ownership") as mock_verify,
            patch("app.services.beat_metrics_service.analyze_audio_file") as mock_analyze,
        ):

            mock_verify.return_value = AsyncMock()
            mock_analyze.return_value = (sample_core_metrics, sample_extra_metrics)

            with patch("app.services.beat_metrics_service.AudioFileHandler") as MockAudioHandler:
                mock_handler = MagicMock()
                mock_handler.save_upload = AsyncMock(return_value="/tmp/test.mp3")
                mock_handler.cleanup = MagicMock()
                MockAudioHandler.return_value = mock_handler

                audio_content = b"fake audio content"
                files = {"audioFile": ("test.mp3", BytesIO(audio_content), "audio/mpeg")}
                data = {"beatId": "beat_admin_delete"}

                create_response = await client_with_test_db.post(
                    "/api/v1/analytics/beat-metrics",
                    data=data,
                    files=files,
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": "admin123",
                        "x-roles": '["admin", "user"]',
                    },
                )

                beat_metrics_id = create_response.json()["id"]

                # Now delete as admin
                delete_response = await client_with_test_db.delete(
                    f"/api/v1/analytics/beat-metrics/{beat_metrics_id}",
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": "admin123",
                        "x-roles": '["admin", "user"]',
                    },
                )

                assert delete_response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.endpoints.beat_metrics.get_current_user")
    async def test_delete_beat_metrics_not_found(
        self, mock_auth, client_with_test_db, mock_user_regular
    ):
        """Test deletion of non-existent beat metrics"""
        mock_auth.return_value = mock_user_regular
        fake_id = "507f191e810c19729de860ea"

        response = await client_with_test_db.delete(
            f"/api/v1/analytics/beat-metrics/{fake_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]',
            },
        )

        assert response.status_code == 404
