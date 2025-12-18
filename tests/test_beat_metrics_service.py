"""
Unit tests for BeatMetricsService
Tests all business logic methods with mocked dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from datetime import datetime

from app.services.beat_metrics_service import BeatMetricsService
from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException, AudioProcessingException
from app.schemas.beat_metrics import BeatMetricsCreate, BeatMetricsUpdate


@pytest.fixture
def mock_db():
    """Create a mock database instance"""
    db = MagicMock()
    db.beat_metrics = MagicMock()
    return db


@pytest.fixture
def beat_metrics_service(mock_db):
    """Create a BeatMetricsService instance with mocked dependencies"""
    return BeatMetricsService(mock_db)


# ==================== Test validate_object_id ====================


class TestValidateObjectId:
    """Test validate_object_id static method"""

    def test_validate_object_id_valid(self, beat_metrics_service):
        """Test validation with valid ObjectId"""
        valid_id = "507f191e810c19729de860ea"
        result = beat_metrics_service.validate_object_id(valid_id)
        assert isinstance(result, ObjectId)
        assert str(result) == valid_id

    def test_validate_object_id_invalid_format(self, beat_metrics_service):
        """Test validation with invalid ObjectId format"""
        with pytest.raises(BadRequestException) as exc_info:
            beat_metrics_service.validate_object_id("invalid_id")
        assert "Invalid BeatMetrics ID" in str(exc_info.value)

    def test_validate_object_id_empty_string(self, beat_metrics_service):
        """Test validation with empty string"""
        with pytest.raises(BadRequestException):
            beat_metrics_service.validate_object_id("")


# ==================== Test serialize ====================


class TestSerialize:
    """Test serialize static method"""

    def test_serialize_with_id(self, beat_metrics_service):
        """Test serialization of document with _id field"""
        doc = {
            "_id": ObjectId("507f191e810c19729de860ea"),
            "beatId": "beat123",
            "coreMetrics": {"energy": 0.8}
        }
        result = beat_metrics_service.serialize(doc)
        assert "id" in result
        assert result["id"] == "507f191e810c19729de860ea"
        assert "_id" not in result

    def test_serialize_without_id(self, beat_metrics_service):
        """Test serialization of document without _id field"""
        doc = {"beatId": "beat123", "coreMetrics": {"energy": 0.8}}
        result = beat_metrics_service.serialize(doc)
        assert "_id" not in result

    def test_serialize_preserves_other_fields(self, beat_metrics_service):
        """Test that serialization preserves all other fields"""
        doc = {
            "_id": ObjectId("507f191e810c19729de860ea"),
            "beatId": "beat123",
            "coreMetrics": {"energy": 0.8},
            "extraMetrics": {"bpm": 120}
        }
        result = beat_metrics_service.serialize(doc)
        assert result["beatId"] == "beat123"
        assert result["coreMetrics"] == {"energy": 0.8}
        assert result["extraMetrics"] == {"bpm": 120}

    def test_serialize_none(self, beat_metrics_service):
        """Test serialization handles None _id gracefully"""
        doc = {"_id": None, "beatId": "beat123"}
        result = beat_metrics_service.serialize(doc)
        assert result["id"] == "None"
        assert "_id" not in result


# ==================== Test get_all ====================


class TestGetAll:
    """Test get_all method"""

    @pytest.mark.asyncio
    async def test_get_all_success(self, beat_metrics_service, mock_db, mock_beat_metrics_doc):
        """Test successful retrieval of all beat metrics"""
        expected_id = str(mock_beat_metrics_doc["_id"])
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__aiter__.return_value = [mock_beat_metrics_doc.copy()]
        mock_db.beat_metrics.find.return_value = mock_cursor

        result = await beat_metrics_service.get_all(skip=0, limit=10)

        assert len(result) == 1
        assert result[0]["id"] == expected_id
        assert result[0]["beatId"] == "beat123"
        mock_db.beat_metrics.find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_all_with_beat_id_filter(self, beat_metrics_service, mock_db, mock_beat_metrics_doc):
        """Test retrieval with beat_id filter"""
        expected_id = str(mock_beat_metrics_doc["_id"])
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__aiter__.return_value = [mock_beat_metrics_doc.copy()]
        mock_db.beat_metrics.find.return_value = mock_cursor

        result = await beat_metrics_service.get_all(beat_id="beat123", skip=0, limit=10)

        assert len(result) == 1
        assert result[0]["beatId"] == "beat123"
        mock_db.beat_metrics.find.assert_called_once_with({"beatId": "beat123"})

    @pytest.mark.asyncio
    async def test_get_all_empty(self, beat_metrics_service, mock_db):
        """Test retrieval when no metrics exist"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__aiter__.return_value = []
        mock_db.beat_metrics.find.return_value = mock_cursor

        result = await beat_metrics_service.get_all(skip=0, limit=10)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, beat_metrics_service, mock_db):
        """Test retrieval with pagination parameters"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__aiter__.return_value = []
        mock_db.beat_metrics.find.return_value = mock_cursor

        await beat_metrics_service.get_all(skip=10, limit=20)

        mock_cursor.skip.assert_called_once_with(10)
        mock_cursor.limit.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_get_all_database_error(self, beat_metrics_service, mock_db):
        """Test handling of database errors"""
        mock_db.beat_metrics.find.side_effect = Exception("Database connection failed")

        with pytest.raises(DatabaseException) as exc_info:
            await beat_metrics_service.get_all(skip=0, limit=10)
        assert "Failed to retrieve beat metrics" in str(exc_info.value)


# ==================== Test get_by_id ====================


class TestGetById:
    """Test get_by_id method"""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, beat_metrics_service, mock_db, mock_beat_metrics_doc):
        """Test successful retrieval by ID"""
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])
        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        result = await beat_metrics_service.get_by_id(beat_metrics_id)

        assert result["id"] == beat_metrics_id
        assert result["beatId"] == "beat123"
        mock_db.beat_metrics.find_one.assert_called_once_with({"_id": ObjectId(beat_metrics_id)})

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, beat_metrics_service, mock_db):
        """Test retrieval of non-existent metrics"""
        beat_metrics_id = "507f191e810c19729de860ea"
        mock_db.beat_metrics.find_one = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException) as exc_info:
            await beat_metrics_service.get_by_id(beat_metrics_id)
        assert beat_metrics_id in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id_invalid_format(self, beat_metrics_service, mock_db):
        """Test retrieval with invalid ID format"""
        with pytest.raises(BadRequestException):
            await beat_metrics_service.get_by_id("invalid_id")

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, beat_metrics_service, mock_db):
        """Test handling of database errors"""
        beat_metrics_id = "507f191e810c19729de860ea"
        mock_db.beat_metrics.find_one = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(DatabaseException) as exc_info:
            await beat_metrics_service.get_by_id(beat_metrics_id)
        assert "Failed to retrieve beat metrics" in str(exc_info.value)


# ==================== Test create ====================


class TestCreate:
    """Test create method"""

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    @patch('app.services.beat_metrics_service.analyze_audio_file')
    async def test_create_success_with_audio_file(
        self,
        mock_analyze,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_beat_metrics_data,
        mock_audio_analysis_result
    ):
        """Test successful creation with audio file upload"""
        mock_verify_ownership.return_value = AsyncMock()
        mock_analyze.return_value = mock_audio_analysis_result

        # Mock audio file handler
        beat_metrics_service.audio_handler.save_upload = AsyncMock(return_value="/tmp/audio.mp3")
        beat_metrics_service.audio_handler.cleanup = MagicMock()

        # Mock upload file
        mock_file = MagicMock()
        mock_file.filename = "test.mp3"

        expected_id = str(mock_beat_metrics_doc["_id"])
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = mock_beat_metrics_doc["_id"]
        mock_db.beat_metrics.insert_one = AsyncMock(return_value=mock_insert_result)
        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        beat_metrics_create = BeatMetricsCreate(**sample_beat_metrics_data)
        result = await beat_metrics_service.create(
            beat_metrics_create,
            user_id="user123",
            is_admin=False,
            audio_file=mock_file
        )

        assert result["id"] == expected_id
        assert result["beatId"] == "beat123"
        mock_verify_ownership.assert_called_once()
        beat_metrics_service.audio_handler.save_upload.assert_called_once()
        beat_metrics_service.audio_handler.cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    @patch('app.services.beat_metrics_service.analyze_audio_file')
    async def test_create_success_with_audio_url(
        self,
        mock_analyze,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_beat_metrics_data,
        mock_audio_analysis_result
    ):
        """Test successful creation with audio URL"""
        mock_verify_ownership.return_value = AsyncMock()
        mock_analyze.return_value = mock_audio_analysis_result

        # Mock audio file handler
        beat_metrics_service.audio_handler.download_from_url = AsyncMock(return_value="/tmp/audio.mp3")
        beat_metrics_service.audio_handler.cleanup = MagicMock()

        expected_id = str(mock_beat_metrics_doc["_id"])
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = mock_beat_metrics_doc["_id"]
        mock_db.beat_metrics.insert_one = AsyncMock(return_value=mock_insert_result)
        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        beat_metrics_create = BeatMetricsCreate(**sample_beat_metrics_data)
        result = await beat_metrics_service.create(
            beat_metrics_create,
            user_id="user123",
            is_admin=False,
            audio_file=None
        )

        assert result["id"] == expected_id
        beat_metrics_service.audio_handler.download_from_url.assert_called_once()
        beat_metrics_service.audio_handler.cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_create_no_audio_source(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        sample_beat_metrics_data
    ):
        """Test creation fails when no audio file or URL provided"""
        mock_verify_ownership.return_value = AsyncMock()

        data = sample_beat_metrics_data.copy()
        data["audioUrl"] = None
        beat_metrics_create = BeatMetricsCreate(**data)

        with pytest.raises(BadRequestException) as exc_info:
            await beat_metrics_service.create(
                beat_metrics_create,
                user_id="user123",
                is_admin=False,
                audio_file=None
            )
        assert "audio file upload or audioUrl must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    @patch('app.services.beat_metrics_service.analyze_audio_file')
    async def test_create_audio_analysis_fails(
        self,
        mock_analyze,
        mock_verify_ownership,
        beat_metrics_service,
        sample_beat_metrics_data
    ):
        """Test creation fails when audio analysis fails"""
        mock_verify_ownership.return_value = AsyncMock()
        mock_analyze.side_effect = Exception("Analysis failed")

        beat_metrics_service.audio_handler.save_upload = AsyncMock(return_value="/tmp/audio.mp3")
        beat_metrics_service.audio_handler.cleanup = MagicMock()

        mock_file = MagicMock()
        beat_metrics_create = BeatMetricsCreate(**sample_beat_metrics_data)

        with pytest.raises(AudioProcessingException) as exc_info:
            await beat_metrics_service.create(
                beat_metrics_create,
                user_id="user123",
                is_admin=False,
                audio_file=mock_file
            )
        assert "Failed to analyze audio file" in str(exc_info.value)
        beat_metrics_service.audio_handler.cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_create_user_doesnt_own_beat(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        sample_beat_metrics_data
    ):
        """Test creation fails when user doesn't own the beat"""
        mock_verify_ownership.side_effect = BadRequestException("User doesn't own the beat")

        beat_metrics_create = BeatMetricsCreate(**sample_beat_metrics_data)

        with pytest.raises(BadRequestException) as exc_info:
            await beat_metrics_service.create(
                beat_metrics_create,
                user_id="user999",
                is_admin=False,
                audio_file=None
            )
        assert "doesn't own" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_create_admin_can_create_any(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_beat_metrics_data,
        mock_audio_analysis_result
    ):
        """Test admin can create metrics for any beat"""
        mock_verify_ownership.return_value = AsyncMock()

        with patch('app.services.beat_metrics_service.analyze_audio_file') as mock_analyze:
            mock_analyze.return_value = mock_audio_analysis_result
            beat_metrics_service.audio_handler.save_upload = AsyncMock(return_value="/tmp/audio.mp3")
            beat_metrics_service.audio_handler.cleanup = MagicMock()

            mock_file = MagicMock()
            expected_id = str(mock_beat_metrics_doc["_id"])
            mock_insert_result = MagicMock()
            mock_insert_result.inserted_id = mock_beat_metrics_doc["_id"]
            mock_db.beat_metrics.insert_one = AsyncMock(return_value=mock_insert_result)
            mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

            beat_metrics_create = BeatMetricsCreate(**sample_beat_metrics_data)
            result = await beat_metrics_service.create(
                beat_metrics_create,
                user_id="admin123",
                is_admin=True,
                audio_file=mock_file
            )

            assert result["id"] == expected_id
            mock_verify_ownership.assert_called_once_with("beat123", "admin123", True)


# ==================== Test update ====================


class TestUpdate:
    """Test update method"""

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_update_success(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_beat_metrics_update_data
    ):
        """Test successful update"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(side_effect=[
            mock_beat_metrics_doc.copy(),  # First call for ownership check
            mock_beat_metrics_doc.copy()   # Second call after update
        ])

        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_db.beat_metrics.update_one = AsyncMock(return_value=mock_update_result)

        beat_metrics_update = BeatMetricsUpdate(**sample_beat_metrics_update_data)
        result = await beat_metrics_service.update(
            beat_metrics_id,
            beat_metrics_update,
            user_id="user123",
            is_admin=False
        )

        assert result["id"] == beat_metrics_id
        mock_verify_ownership.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, beat_metrics_service, mock_db, sample_core_metrics):
        """Test update of non-existent metrics"""
        beat_metrics_id = "507f191e810c19729de860ea"
        mock_db.beat_metrics.find_one = AsyncMock(return_value=None)

        from app.models.beat_metrics import CoreMetrics
        beat_metrics_update = BeatMetricsUpdate(coreMetrics=CoreMetrics(**sample_core_metrics))

        with pytest.raises(NotFoundException) as exc_info:
            await beat_metrics_service.update(
                beat_metrics_id,
                beat_metrics_update,
                user_id="user123",
                is_admin=False
            )
        assert beat_metrics_id in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_update_user_doesnt_own_beat(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_core_metrics
    ):
        """Test update fails when user doesn't own the beat"""
        mock_verify_ownership.side_effect = BadRequestException("User doesn't own the beat")
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        from app.models.beat_metrics import CoreMetrics
        beat_metrics_update = BeatMetricsUpdate(coreMetrics=CoreMetrics(**sample_core_metrics))

        with pytest.raises(BadRequestException) as exc_info:
            await beat_metrics_service.update(
                beat_metrics_id,
                beat_metrics_update,
                user_id="user999",
                is_admin=False
            )
        assert "doesn't own" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_update_admin_can_update_any(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_beat_metrics_update_data
    ):
        """Test admin can update any metrics"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(side_effect=[
            mock_beat_metrics_doc.copy(),
            mock_beat_metrics_doc.copy()
        ])

        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_db.beat_metrics.update_one = AsyncMock(return_value=mock_update_result)

        beat_metrics_update = BeatMetricsUpdate(**sample_beat_metrics_update_data)
        result = await beat_metrics_service.update(
            beat_metrics_id,
            beat_metrics_update,
            user_id="admin123",
            is_admin=True
        )

        assert result["id"] == beat_metrics_id
        mock_verify_ownership.assert_called_once_with("beat123", "admin123", True)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_update_database_error(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc,
        sample_core_metrics
    ):
        """Test handling of database errors during update"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())
        mock_db.beat_metrics.update_one = AsyncMock(side_effect=Exception("Database error"))

        from app.models.beat_metrics import CoreMetrics
        beat_metrics_update = BeatMetricsUpdate(coreMetrics=CoreMetrics(**sample_core_metrics))

        with pytest.raises(DatabaseException) as exc_info:
            await beat_metrics_service.update(
                beat_metrics_id,
                beat_metrics_update,
                user_id="user123",
                is_admin=False
            )
        assert "Failed to update beat metrics" in str(exc_info.value)


# ==================== Test delete ====================


class TestDelete:
    """Test delete method"""

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_delete_success(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc
    ):
        """Test successful deletion"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_db.beat_metrics.delete_one = AsyncMock(return_value=mock_delete_result)

        await beat_metrics_service.delete(beat_metrics_id, user_id="user123", is_admin=False)

        mock_verify_ownership.assert_called_once()
        mock_db.beat_metrics.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, beat_metrics_service, mock_db):
        """Test deletion of non-existent metrics"""
        beat_metrics_id = "507f191e810c19729de860ea"
        mock_db.beat_metrics.find_one = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException) as exc_info:
            await beat_metrics_service.delete(beat_metrics_id, user_id="user123", is_admin=False)
        assert beat_metrics_id in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_delete_user_doesnt_own_beat(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc
    ):
        """Test deletion fails when user doesn't own the beat"""
        mock_verify_ownership.side_effect = BadRequestException("User doesn't own the beat")
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        with pytest.raises(BadRequestException) as exc_info:
            await beat_metrics_service.delete(beat_metrics_id, user_id="user999", is_admin=False)
        assert "doesn't own" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_delete_admin_can_delete_any(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc
    ):
        """Test admin can delete any metrics"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())

        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_db.beat_metrics.delete_one = AsyncMock(return_value=mock_delete_result)

        await beat_metrics_service.delete(beat_metrics_id, user_id="admin123", is_admin=True)

        mock_verify_ownership.assert_called_once_with("beat123", "admin123", True)

    @pytest.mark.asyncio
    @patch('app.services.beat_metrics_service.verify_beat_ownership')
    async def test_delete_database_error(
        self,
        mock_verify_ownership,
        beat_metrics_service,
        mock_db,
        mock_beat_metrics_doc
    ):
        """Test handling of database errors during deletion"""
        mock_verify_ownership.return_value = AsyncMock()
        beat_metrics_id = str(mock_beat_metrics_doc["_id"])

        mock_db.beat_metrics.find_one = AsyncMock(return_value=mock_beat_metrics_doc.copy())
        mock_db.beat_metrics.delete_one = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(DatabaseException) as exc_info:
            await beat_metrics_service.delete(beat_metrics_id, user_id="user123", is_admin=False)
        assert "Failed to delete beat metrics" in str(exc_info.value)


# ==================== Test ensure_indexes ====================


class TestEnsureIndexes:
    """Test ensure_indexes method"""

    @pytest.mark.asyncio
    async def test_ensure_indexes_success(self, beat_metrics_service, mock_db):
        """Test successful index creation"""
        mock_db.beat_metrics.create_index = AsyncMock()

        await beat_metrics_service.ensure_indexes()

        mock_db.beat_metrics.create_index.assert_called_once_with("beatId")

    @pytest.mark.asyncio
    async def test_ensure_indexes_failure(self, beat_metrics_service, mock_db):
        """Test handling of index creation failure"""
        mock_db.beat_metrics.create_index = AsyncMock(side_effect=Exception("Index creation failed"))

        with pytest.raises(DatabaseException) as exc_info:
            await beat_metrics_service.ensure_indexes()
        assert "Failed to create indexes" in str(exc_info.value)
