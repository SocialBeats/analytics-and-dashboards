"""
Unit tests for DashboardService

Tests the business logic layer with minimal dependencies.
Uses mocking to isolate the service from external dependencies.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from bson.errors import InvalidId

from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardCreate, DashboardUpdate
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    DatabaseException
)


@pytest_asyncio.fixture
async def mock_db():
    """Mock database instance"""
    db = MagicMock()
    db.dashboards = MagicMock()
    return db


@pytest_asyncio.fixture
async def dashboard_service(mock_db):
    """Create DashboardService instance with mock database"""
    return DashboardService(mock_db)


@pytest.fixture
def sample_dashboard_doc():
    """Sample dashboard document from database"""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "owner_id": "user123",
        "beat_id": "beat123",
        "name": "Test Dashboard",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }


@pytest.fixture
def dashboard_create_data():
    """Sample dashboard creation schema"""
    return DashboardCreate(name="New Dashboard", beatId="beat123")


@pytest.fixture
def dashboard_update_data():
    """Sample dashboard update schema"""
    return DashboardUpdate(name="Updated Dashboard")


# ==================== Tests for validate_object_id ====================


class TestValidateObjectId:
    """Tests for ObjectId validation"""

    def test_validate_object_id_valid(self):
        """POSITIVE: Valid ObjectId string should be converted to ObjectId"""
        valid_id = "507f1f77bcf86cd799439011"
        result = DashboardService.validate_object_id(valid_id)

        assert isinstance(result, ObjectId)
        assert str(result) == valid_id

    def test_validate_object_id_invalid_format(self):
        """NEGATIVE: Invalid ObjectId format should raise BadRequestException"""
        invalid_id = "invalid_id_123"

        with pytest.raises(BadRequestException) as exc_info:
            DashboardService.validate_object_id(invalid_id)

        assert "Invalid dashboard ID format" in str(exc_info.value.detail)
        assert invalid_id in str(exc_info.value.detail)

    def test_validate_object_id_empty_string(self):
        """NEGATIVE: Empty string should raise BadRequestException"""
        with pytest.raises(BadRequestException):
            DashboardService.validate_object_id("")

    def test_validate_object_id_none(self):
        """NEGATIVE: None should raise BadRequestException"""
        with pytest.raises(BadRequestException):
            DashboardService.validate_object_id(None)


# ==================== Tests for serialize ====================


class TestSerialize:
    """Tests for document serialization"""

    def test_serialize_with_id(self):
        """POSITIVE: Document with _id should be converted to id string"""
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Test",
            "owner_id": "user123"
        }

        result = DashboardService.serialize(doc)

        assert "id" in result
        assert "_id" not in result
        assert result["id"] == "507f1f77bcf86cd799439011"
        assert result["name"] == "Test"

    def test_serialize_without_id(self):
        """POSITIVE: Document without _id should remain unchanged"""
        doc = {"name": "Test", "owner_id": "user123"}

        result = DashboardService.serialize(doc)

        assert result == doc
        assert "_id" not in result
        assert "id" not in result

    def test_serialize_none(self):
        """NEGATIVE: None should return None"""
        result = DashboardService.serialize(None)
        assert result is None

    def test_serialize_empty_dict(self):
        """POSITIVE: Empty dict should return empty dict"""
        result = DashboardService.serialize({})
        assert result == {}


# ==================== Tests for get_all ====================


class TestGetAll:
    """Tests for getting all dashboards"""

    @pytest.mark.asyncio
    async def test_get_all_success(self, dashboard_service, mock_db, sample_dashboard_doc):
        """POSITIVE: Should return all dashboards with pagination"""
        # Arrange
        expected_id = str(sample_dashboard_doc["_id"])
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_dashboard_doc.copy()])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        result = await dashboard_service.get_all(skip=0, limit=10)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == expected_id
        assert "_id" not in result[0]
        assert result[0]["name"] == sample_dashboard_doc["name"]
        mock_db.dashboards.find.assert_called_once()
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, dashboard_service, mock_db):
        """POSITIVE: Should return empty list when no dashboards exist"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        result = await dashboard_service.get_all()

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, dashboard_service, mock_db, sample_dashboard_doc):
        """POSITIVE: Should apply skip and limit correctly"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_dashboard_doc])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        result = await dashboard_service.get_all(skip=10, limit=5)

        # Assert
        mock_cursor.skip.assert_called_once_with(10)
        mock_cursor.limit.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_get_all_database_error(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(side_effect=Exception("Connection lost"))
        mock_db.dashboards.find.return_value = mock_cursor

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.get_all()

        assert "Failed to retrieve dashboards" in str(exc_info.value.detail)


# ==================== Tests for get_by_owner ====================


class TestGetByOwner:
    """Tests for getting dashboards by owner"""

    @pytest.mark.asyncio
    async def test_get_by_owner_success(self, dashboard_service, mock_db, sample_dashboard_doc):
        """POSITIVE: Should return dashboards owned by specific user"""
        # Arrange
        owner_id = "user123"
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_dashboard_doc])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        result = await dashboard_service.get_by_owner(owner_id)

        # Assert
        assert len(result) == 1
        assert result[0]["owner_id"] == owner_id
        mock_db.dashboards.find.assert_called_once_with({"owner_id": owner_id})

    @pytest.mark.asyncio
    async def test_get_by_owner_no_results(self, dashboard_service, mock_db):
        """POSITIVE: Should return empty list when user has no dashboards"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        result = await dashboard_service.get_by_owner("user_without_dashboards")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_owner_with_pagination(self, dashboard_service, mock_db):
        """POSITIVE: Should apply pagination to owner query"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.dashboards.find.return_value = mock_cursor

        # Act
        await dashboard_service.get_by_owner("user123", skip=5, limit=20)

        # Assert
        mock_cursor.skip.assert_called_once_with(5)
        mock_cursor.limit.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_get_by_owner_database_error(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(side_effect=Exception("Database error"))
        mock_db.dashboards.find.return_value = mock_cursor

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.get_by_owner("user123")

        assert "Failed to retrieve user dashboards" in str(exc_info.value.detail)


# ==================== Tests for get_by_id ====================


class TestGetById:
    """Tests for getting dashboard by ID"""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, dashboard_service, mock_db, sample_dashboard_doc):
        """POSITIVE: Should return dashboard when found"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)

        # Act
        result = await dashboard_service.get_by_id(dashboard_id)

        # Assert
        assert result["id"] == dashboard_id
        assert "_id" not in result
        assert result["name"] == sample_dashboard_doc["name"]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise NotFoundException when dashboard doesn't exist"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await dashboard_service.get_by_id(dashboard_id)

        assert "Dashboard" in str(exc_info.value.detail)
        assert dashboard_id in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_by_id_invalid_format(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise BadRequestException for invalid ID format"""
        # Arrange
        invalid_id = "invalid_id"

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.get_by_id(invalid_id)

        assert "Invalid dashboard ID format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.get_by_id(dashboard_id)

        assert "Failed to retrieve dashboard" in str(exc_info.value.detail)


# ==================== Tests for create ====================


class TestCreate:
    """Tests for creating dashboards"""

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_success(
        self,
        mock_verify,
        dashboard_service,
        mock_db,
        dashboard_create_data,
        sample_dashboard_doc
    ):
        """POSITIVE: Should create dashboard successfully"""
        # Arrange
        owner_id = "user123"
        expected_id = str(sample_dashboard_doc["_id"])
        mock_verify.return_value = {"beatId": "beat123", "ownerId": owner_id}
        mock_result = MagicMock()
        mock_result.inserted_id = sample_dashboard_doc["_id"]
        mock_db.dashboards.insert_one = AsyncMock(return_value=mock_result)
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc.copy())

        # Act
        result = await dashboard_service.create(dashboard_create_data, owner_id)

        # Assert
        assert result["id"] == expected_id
        assert result["owner_id"] == owner_id
        mock_verify.assert_called_once_with("beat123", owner_id, False)
        mock_db.dashboards.insert_one.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_admin_bypass_ownership(
        self,
        mock_verify,
        dashboard_service,
        mock_db,
        dashboard_create_data,
        sample_dashboard_doc
    ):
        """POSITIVE: Admin should bypass beat ownership check"""
        # Arrange
        owner_id = "admin123"
        mock_verify.return_value = {"beatId": "beat123", "ownerId": owner_id}
        mock_result = MagicMock()
        mock_result.inserted_id = sample_dashboard_doc["_id"]
        mock_db.dashboards.insert_one = AsyncMock(return_value=mock_result)
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)

        # Act
        result = await dashboard_service.create(dashboard_create_data, owner_id, is_admin=True)

        # Assert
        assert result is not None
        mock_verify.assert_called_once_with("beat123", owner_id, True)

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_beat_not_found(
        self,
        mock_verify,
        dashboard_service,
        dashboard_create_data
    ):
        """NEGATIVE: Should raise NotFoundException when beat doesn't exist"""
        # Arrange
        mock_verify.side_effect = NotFoundException(resource="Beat", resource_id="beat123")

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await dashboard_service.create(dashboard_create_data, "user123")

        assert "Beat" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_user_doesnt_own_beat(
        self,
        mock_verify,
        dashboard_service,
        dashboard_create_data
    ):
        """NEGATIVE: Should raise BadRequestException when user doesn't own beat"""
        # Arrange
        mock_verify.side_effect = BadRequestException("You don't have access to this beat")

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.create(dashboard_create_data, "user123")

        assert "access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_duplicate_name(
        self,
        mock_verify,
        dashboard_service,
        mock_db,
        dashboard_create_data
    ):
        """NEGATIVE: Should raise BadRequestException for duplicate dashboard name"""
        # Arrange
        mock_verify.return_value = {"beatId": "beat123", "ownerId": "user123"}
        mock_db.dashboards.insert_one = AsyncMock(
            side_effect=Exception("duplicate key error collection")
        )

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.create(dashboard_create_data, "user123")

        assert "unique" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @patch('app.services.dashboard_service.verify_beat_ownership')
    async def test_create_database_error(
        self,
        mock_verify,
        dashboard_service,
        mock_db,
        dashboard_create_data
    ):
        """NEGATIVE: Should raise DatabaseException on general database error"""
        # Arrange
        mock_verify.return_value = {"beatId": "beat123", "ownerId": "user123"}
        mock_db.dashboards.insert_one = AsyncMock(side_effect=Exception("Connection failed"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.create(dashboard_create_data, "user123")

        assert "Failed to create dashboard" in str(exc_info.value.detail)


# ==================== Tests for update ====================


class TestUpdate:
    """Tests for updating dashboards"""

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        dashboard_service,
        mock_db,
        dashboard_update_data,
        sample_dashboard_doc
    ):
        """POSITIVE: Should update dashboard successfully"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        user_id = "user123"
        updated_doc = {**sample_dashboard_doc, "name": "Updated Dashboard", "updated_at": datetime.utcnow()}
        mock_db.dashboards.find_one = AsyncMock(side_effect=[sample_dashboard_doc, updated_doc])
        mock_db.dashboards.update_one = AsyncMock()

        # Act
        result = await dashboard_service.update(dashboard_id, dashboard_update_data, user_id)

        # Assert
        assert result["name"] == "Updated Dashboard"
        assert result["updated_at"] is not None
        mock_db.dashboards.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, dashboard_service, mock_db, dashboard_update_data):
        """NEGATIVE: Should raise NotFoundException when dashboard doesn't exist"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await dashboard_service.update(dashboard_id, dashboard_update_data, "user123")

        assert "Dashboard" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_not_owner(
        self,
        dashboard_service,
        mock_db,
        dashboard_update_data,
        sample_dashboard_doc
    ):
        """NEGATIVE: Should raise BadRequestException when user is not owner"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        different_user_id = "other_user"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.update(dashboard_id, dashboard_update_data, different_user_id)

        assert "only update your own" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_admin_can_update_any(
        self,
        dashboard_service,
        mock_db,
        dashboard_update_data,
        sample_dashboard_doc
    ):
        """POSITIVE: Admin should be able to update any dashboard"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        admin_id = "admin123"
        updated_doc = {**sample_dashboard_doc, "name": "Updated Dashboard"}
        mock_db.dashboards.find_one = AsyncMock(side_effect=[sample_dashboard_doc, updated_doc])
        mock_db.dashboards.update_one = AsyncMock()

        # Act
        result = await dashboard_service.update(
            dashboard_id,
            dashboard_update_data,
            admin_id,
            is_admin=True
        )

        # Assert
        assert result is not None
        mock_db.dashboards.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_changes(
        self,
        dashboard_service,
        mock_db,
        sample_dashboard_doc
    ):
        """POSITIVE: Should return existing dashboard when no changes provided"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        empty_update = DashboardUpdate()
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)

        # Act
        result = await dashboard_service.update(dashboard_id, empty_update, "user123")

        # Assert
        assert result["name"] == sample_dashboard_doc["name"]
        mock_db.dashboards.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_duplicate_name(
        self,
        dashboard_service,
        mock_db,
        dashboard_update_data,
        sample_dashboard_doc
    ):
        """NEGATIVE: Should raise BadRequestException for duplicate name"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)
        mock_db.dashboards.update_one = AsyncMock(
            side_effect=Exception("duplicate key error")
        )

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.update(dashboard_id, dashboard_update_data, "user123")

        assert "unique" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_invalid_id(self, dashboard_service, dashboard_update_data):
        """NEGATIVE: Should raise BadRequestException for invalid ID"""
        # Arrange
        invalid_id = "invalid_id"

        # Act & Assert
        with pytest.raises(BadRequestException):
            await dashboard_service.update(invalid_id, dashboard_update_data, "user123")


# ==================== Tests for delete ====================


class TestDelete:
    """Tests for deleting dashboards"""

    @pytest.mark.asyncio
    async def test_delete_success(self, dashboard_service, mock_db, sample_dashboard_doc):
        """POSITIVE: Should delete dashboard successfully"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        user_id = "user123"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)
        mock_db.dashboards.delete_one = AsyncMock()

        # Act
        result = await dashboard_service.delete(dashboard_id, user_id)

        # Assert
        assert "message" in result
        assert "successfully" in result["message"].lower()
        assert result["id"] == dashboard_id
        mock_db.dashboards.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise NotFoundException when dashboard doesn't exist"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await dashboard_service.delete(dashboard_id, "user123")

        assert "Dashboard" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_not_owner(self, dashboard_service, mock_db, sample_dashboard_doc):
        """NEGATIVE: Should raise BadRequestException when user is not owner"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        different_user_id = "other_user"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await dashboard_service.delete(dashboard_id, different_user_id)

        assert "only delete your own" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_delete_admin_can_delete_any(
        self,
        dashboard_service,
        mock_db,
        sample_dashboard_doc
    ):
        """POSITIVE: Admin should be able to delete any dashboard"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        admin_id = "admin123"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)
        mock_db.dashboards.delete_one = AsyncMock()

        # Act
        result = await dashboard_service.delete(dashboard_id, admin_id, is_admin=True)

        # Assert
        assert result is not None
        mock_db.dashboards.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_invalid_id(self, dashboard_service):
        """NEGATIVE: Should raise BadRequestException for invalid ID"""
        # Arrange
        invalid_id = "invalid_id"

        # Act & Assert
        with pytest.raises(BadRequestException):
            await dashboard_service.delete(invalid_id, "user123")

    @pytest.mark.asyncio
    async def test_delete_database_error(self, dashboard_service, mock_db, sample_dashboard_doc):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        dashboard_id = "507f1f77bcf86cd799439011"
        mock_db.dashboards.find_one = AsyncMock(return_value=sample_dashboard_doc)
        mock_db.dashboards.delete_one = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.delete(dashboard_id, "user123")

        assert "Failed to delete dashboard" in str(exc_info.value.detail)


# ==================== Tests for count ====================


class TestCount:
    """Tests for counting dashboards"""

    @pytest.mark.asyncio
    async def test_count_success(self, dashboard_service, mock_db):
        """POSITIVE: Should return correct count of dashboards"""
        # Arrange
        expected_count = 42
        mock_db.dashboards.count_documents = AsyncMock(return_value=expected_count)

        # Act
        result = await dashboard_service.count()

        # Assert
        assert result == expected_count
        mock_db.dashboards.count_documents.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_count_zero(self, dashboard_service, mock_db):
        """POSITIVE: Should return 0 when no dashboards exist"""
        # Arrange
        mock_db.dashboards.count_documents = AsyncMock(return_value=0)

        # Act
        result = await dashboard_service.count()

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_database_error(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_db.dashboards.count_documents = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.count()

        assert "Failed to count dashboards" in str(exc_info.value.detail)


# ==================== Tests for ensure_indexes ====================


class TestEnsureIndexes:
    """Tests for index creation"""

    @pytest.mark.asyncio
    async def test_ensure_indexes_success(self, dashboard_service, mock_db):
        """POSITIVE: Should create indexes successfully"""
        # Arrange
        mock_db.dashboards.create_index = AsyncMock()

        # Act
        await dashboard_service.ensure_indexes()

        # Assert
        assert mock_db.dashboards.create_index.call_count == 3
        calls = mock_db.dashboards.create_index.call_args_list
        assert calls[0][0][0] == "name"
        assert calls[0][1]["unique"] is True

    @pytest.mark.asyncio
    async def test_ensure_indexes_failure(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on index creation failure"""
        # Arrange
        mock_db.dashboards.create_index = AsyncMock(side_effect=Exception("Index error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.ensure_indexes()

        assert "Failed to create indexes" in str(exc_info.value.detail)


# ==================== Tests for seed_initial ====================


class TestSeedInitial:
    """Tests for initial data seeding"""

    @pytest.mark.asyncio
    async def test_seed_initial_when_empty(self, dashboard_service, mock_db):
        """POSITIVE: Should seed initial dashboards when collection is empty"""
        # Arrange
        mock_db.dashboards.count_documents = AsyncMock(return_value=0)
        mock_db.dashboards.insert_many = AsyncMock()

        # Act
        await dashboard_service.seed_initial()

        # Assert
        mock_db.dashboards.insert_many.assert_called_once()
        inserted_data = mock_db.dashboards.insert_many.call_args[0][0]
        assert len(inserted_data) == 2
        assert inserted_data[0]["name"] == "General"
        assert inserted_data[1]["name"] == "Ventas"

    @pytest.mark.asyncio
    async def test_seed_initial_skip_when_not_empty(self, dashboard_service, mock_db):
        """POSITIVE: Should skip seeding when dashboards already exist"""
        # Arrange
        mock_db.dashboards.count_documents = AsyncMock(return_value=5)
        mock_db.dashboards.insert_many = AsyncMock()

        # Act
        await dashboard_service.seed_initial()

        # Assert
        mock_db.dashboards.insert_many.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_initial_database_error(self, dashboard_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on seeding failure"""
        # Arrange
        mock_db.dashboards.count_documents = AsyncMock(return_value=0)
        mock_db.dashboards.insert_many = AsyncMock(side_effect=Exception("Insert failed"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await dashboard_service.seed_initial()

        assert "Failed to seed dashboards" in str(exc_info.value.detail)
