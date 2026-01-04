"""
Unit tests for WidgetService

Tests the business logic layer with minimal dependencies.
Uses mocking to isolate the service from external dependencies.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from bson.errors import InvalidId

from app.services.widget_service import WidgetService
from app.schemas.widget import WidgetCreate, WidgetUpdate
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    DatabaseException
)


@pytest_asyncio.fixture
async def mock_db():
    """Mock database instance"""
    db = MagicMock()
    db.widgets = MagicMock()
    db.dashboards = MagicMock()
    return db


@pytest_asyncio.fixture
async def widget_service(mock_db):
    """Create WidgetService instance with mock database"""
    return WidgetService(mock_db)


@pytest.fixture
def sample_widget_doc():
    """Sample widget document from database"""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "dashboard_id": "507f191e810c19729de860ea",
        "metric_type": "BPM",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }


@pytest.fixture
def widget_create_data():
    """Sample widget creation schema"""
    return WidgetCreate(dashboardId="507f191e810c19729de860ea", metricType="BPM")


@pytest.fixture
def widget_update_data():
    """Sample widget update schema"""
    return WidgetUpdate(metricType="ENERGY")


# ==================== Tests for validate_object_id ====================


class TestValidateObjectId:
    """Tests for ObjectId validation"""

    def test_validate_object_id_valid(self):
        """POSITIVE: Valid ObjectId string should be converted to ObjectId"""
        valid_id = "507f1f77bcf86cd799439011"
        result = WidgetService.validate_object_id(valid_id)

        assert isinstance(result, ObjectId)
        assert str(result) == valid_id

    def test_validate_object_id_invalid_format(self):
        """NEGATIVE: Invalid ObjectId format should raise BadRequestException"""
        invalid_id = "invalid_id_123"

        with pytest.raises(BadRequestException) as exc_info:
            WidgetService.validate_object_id(invalid_id)

        assert "Invalid widget ID format" in str(exc_info.value.detail)
        assert invalid_id in str(exc_info.value.detail)

    def test_validate_object_id_empty_string(self):
        """NEGATIVE: Empty string should raise BadRequestException"""
        with pytest.raises(BadRequestException):
            WidgetService.validate_object_id("")


# ==================== Tests for serialize_widget ====================


class TestSerializeWidget:
    """Tests for widget serialization"""

    def test_serialize_widget_with_id(self):
        """POSITIVE: Widget with _id should be converted to id string"""
        widget = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "dashboard_id": "dash123",
            "metric_type": "BPM"
        }

        result = WidgetService.serialize_widget(widget)

        assert "id" in result
        assert "_id" not in result
        assert result["id"] == "507f1f77bcf86cd799439011"
        assert result["metric_type"] == "BPM"

    def test_serialize_widget_without_id(self):
        """POSITIVE: Widget without _id should remain unchanged"""
        widget = {"metric_type": "BPM", "dashboard_id": "dash123"}

        result = WidgetService.serialize_widget(widget)

        assert result == widget
        assert "_id" not in result
        assert "id" not in result

    def test_serialize_widget_none(self):
        """NEGATIVE: None should return None"""
        result = WidgetService.serialize_widget(None)
        assert result is None

    def test_serialize_widget_empty_dict(self):
        """POSITIVE: Empty dict should return empty dict"""
        result = WidgetService.serialize_widget({})
        assert result == {}


# ==================== Tests for get_all ====================


class TestGetAll:
    """Tests for getting all widgets"""

    @pytest.mark.asyncio
    async def test_get_all_success(self, widget_service, mock_db, sample_widget_doc):
        """POSITIVE: Should return all widgets"""
        # Arrange
        expected_id = str(sample_widget_doc["_id"])
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_widget_doc.copy()])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        result = await widget_service.get_all()

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == expected_id
        assert "_id" not in result[0]
        assert result[0]["metric_type"] == "BPM"

    @pytest.mark.asyncio
    async def test_get_all_with_dashboard_filter(self, widget_service, mock_db, sample_widget_doc):
        """POSITIVE: Should filter widgets by dashboard_id"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_widget_doc.copy()])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        result = await widget_service.get_all(dashboard_id=dashboard_id)

        # Assert
        mock_db.widgets.find.assert_called_once_with({"dashboard_id": dashboard_id})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_empty(self, widget_service, mock_db):
        """POSITIVE: Should return empty list when no widgets exist"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        result = await widget_service.get_all()

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, widget_service, mock_db):
        """POSITIVE: Should apply skip and limit correctly"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        await widget_service.get_all(skip=10, limit=5)

        # Assert
        mock_cursor.skip.assert_called_once_with(10)
        mock_cursor.limit.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_get_all_database_error(self, widget_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(side_effect=Exception("Connection lost"))
        mock_db.widgets.find.return_value = mock_cursor

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.get_all()

        assert "Failed to retrieve widgets" in str(exc_info.value.detail)


# ==================== Tests for get_by_id ====================


class TestGetById:
    """Tests for getting widget by ID"""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, widget_service, mock_db, sample_widget_doc):
        """POSITIVE: Should return widget when found"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc.copy())

        # Act
        result = await widget_service.get_by_id(widget_id)

        # Assert
        assert result["id"] == widget_id
        assert "_id" not in result
        assert result["metric_type"] == "BPM"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, widget_service, mock_db):
        """NEGATIVE: Should raise NotFoundException when widget doesn't exist"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await widget_service.get_by_id(widget_id)

        assert "Widget" in str(exc_info.value.detail)
        assert widget_id in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_by_id_invalid_format(self, widget_service):
        """NEGATIVE: Should raise BadRequestException for invalid ID format"""
        # Arrange
        invalid_id = "invalid_id"

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.get_by_id(invalid_id)

        assert "Invalid widget ID format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, widget_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.get_by_id(widget_id)

        assert "Failed to retrieve widget" in str(exc_info.value.detail)


# ==================== Tests for verify_dashboard_ownership ====================


class TestVerifyDashboardOwnership:
    """Tests for dashboard ownership verification"""

    @pytest.mark.asyncio
    async def test_verify_dashboard_ownership_success(self, widget_service, mock_db, mock_dashboard_doc):
        """POSITIVE: Should return dashboard when user is owner"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        user_id = "user123"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act
        result = await widget_service.verify_dashboard_ownership(dashboard_id, user_id)

        # Assert
        assert result == mock_dashboard_doc
        mock_db.dashboards.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_dashboard_ownership_admin_bypass(self, widget_service, mock_db, mock_dashboard_doc):
        """POSITIVE: Admin should access any dashboard"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        admin_id = "admin123"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act
        result = await widget_service.verify_dashboard_ownership(dashboard_id, admin_id, is_admin=True)

        # Assert
        assert result == mock_dashboard_doc

    @pytest.mark.asyncio
    async def test_verify_dashboard_ownership_not_found(self, widget_service, mock_db):
        """NEGATIVE: Should raise NotFoundException when dashboard doesn't exist"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        mock_db.dashboards.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await widget_service.verify_dashboard_ownership(dashboard_id, "user123")

        assert "Dashboard" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_dashboard_ownership_not_owner(self, widget_service, mock_db, mock_dashboard_doc):
        """NEGATIVE: Should raise BadRequestException when user is not owner"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        different_user = "other_user"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.verify_dashboard_ownership(dashboard_id, different_user)

        assert "don't have access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_verify_dashboard_ownership_invalid_id(self, widget_service):
        """NEGATIVE: Should raise BadRequestException for invalid dashboard ID"""
        # Arrange
        invalid_id = "invalid_id"

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.verify_dashboard_ownership(invalid_id, "user123")

        assert "Invalid dashboard ID format" in str(exc_info.value.detail)


# ==================== Tests for create ====================


class TestCreate:
    """Tests for creating widgets"""

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        widget_service,
        mock_db,
        widget_create_data,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Should create widget successfully"""
        # Arrange
        user_id = "user123"
        expected_id = str(sample_widget_doc["_id"])
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_result = MagicMock()
        mock_result.inserted_id = sample_widget_doc["_id"]
        mock_db.widgets.insert_one = AsyncMock(return_value=mock_result)
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc.copy())

        # Act
        result = await widget_service.create(widget_create_data, user_id)

        # Assert
        assert result["id"] == expected_id
        assert result["metric_type"] == "BPM"
        mock_db.dashboards.find_one.assert_called_once()
        mock_db.widgets.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_admin_can_create_any(
        self,
        widget_service,
        mock_db,
        widget_create_data,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Admin should be able to create widget on any dashboard"""
        # Arrange
        admin_id = "admin123"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_result = MagicMock()
        mock_result.inserted_id = sample_widget_doc["_id"]
        mock_db.widgets.insert_one = AsyncMock(return_value=mock_result)
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc.copy())

        # Act
        result = await widget_service.create(widget_create_data, admin_id, is_admin=True)

        # Assert
        assert result is not None
        mock_db.widgets.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_dashboard_not_found(self, widget_service, mock_db, widget_create_data):
        """NEGATIVE: Should raise NotFoundException when dashboard doesn't exist"""
        # Arrange
        mock_db.dashboards.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await widget_service.create(widget_create_data, "user123")

        assert "Dashboard" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_doesnt_own_dashboard(
        self,
        widget_service,
        mock_db,
        widget_create_data,
        mock_dashboard_doc
    ):
        """NEGATIVE: Should raise BadRequestException when user doesn't own dashboard"""
        # Arrange
        different_user = "other_user"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.create(widget_create_data, different_user)

        assert "don't have access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        widget_service,
        mock_db,
        widget_create_data,
        mock_dashboard_doc
    ):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.insert_one = AsyncMock(side_effect=Exception("Connection failed"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.create(widget_create_data, "user123")

        assert "Failed to create widget" in str(exc_info.value.detail)


# ==================== Tests for update ====================


class TestUpdate:
    """Tests for updating widgets"""

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        widget_service,
        mock_db,
        widget_update_data,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Should update widget successfully"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        user_id = "user123"
        updated_doc = {**sample_widget_doc, "metric_type": "ENERGY", "updated_at": datetime.utcnow()}
        mock_db.widgets.find_one = AsyncMock(side_effect=[sample_widget_doc, updated_doc])
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.update_one = AsyncMock()

        # Act
        result = await widget_service.update(widget_id, widget_update_data, user_id)

        # Assert
        assert result["metric_type"] == "ENERGY"
        assert result["updated_at"] is not None
        mock_db.widgets.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, widget_service, mock_db, widget_update_data):
        """NEGATIVE: Should raise NotFoundException when widget doesn't exist"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await widget_service.update(widget_id, widget_update_data, "user123")

        assert "Widget" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_doesnt_own_dashboard(
        self,
        widget_service,
        mock_db,
        widget_update_data,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """NEGATIVE: Should raise BadRequestException when user doesn't own dashboard"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        different_user = "other_user"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc)
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.update(widget_id, widget_update_data, different_user)

        assert "don't have access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_admin_can_update_any(
        self,
        widget_service,
        mock_db,
        widget_update_data,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Admin should be able to update any widget"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        admin_id = "admin123"
        updated_doc = {**sample_widget_doc, "metric_type": "ENERGY"}
        mock_db.widgets.find_one = AsyncMock(side_effect=[sample_widget_doc, updated_doc])
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.update_one = AsyncMock()

        # Act
        result = await widget_service.update(widget_id, widget_update_data, admin_id, is_admin=True)

        # Assert
        assert result is not None
        mock_db.widgets.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_changes(self, widget_service, mock_db, sample_widget_doc, mock_dashboard_doc):
        """POSITIVE: Should return existing widget when no changes provided"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        empty_update = WidgetUpdate()
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc.copy())
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act
        result = await widget_service.update(widget_id, empty_update, "user123")

        # Assert
        assert result["metric_type"] == sample_widget_doc["metric_type"]
        mock_db.widgets.update_one.assert_not_called()


# ==================== Tests for delete ====================


class TestDelete:
    """Tests for deleting widgets"""

    @pytest.mark.asyncio
    async def test_delete_success(self, widget_service, mock_db, sample_widget_doc, mock_dashboard_doc):
        """POSITIVE: Should delete widget successfully"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        user_id = "user123"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc)
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.delete_one = AsyncMock()

        # Act
        result = await widget_service.delete(widget_id, user_id)

        # Assert
        assert "message" in result
        assert "successfully" in result["message"].lower()
        assert result["id"] == widget_id
        mock_db.widgets.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, widget_service, mock_db):
        """NEGATIVE: Should raise NotFoundException when widget doesn't exist"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await widget_service.delete(widget_id, "user123")

        assert "Widget" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_user_doesnt_own_dashboard(
        self,
        widget_service,
        mock_db,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """NEGATIVE: Should raise BadRequestException when user doesn't own dashboard"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        different_user = "other_user"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc)
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.delete(widget_id, different_user)

        assert "don't have access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_delete_admin_can_delete_any(
        self,
        widget_service,
        mock_db,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Admin should be able to delete any widget"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        admin_id = "admin123"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc)
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.delete_one = AsyncMock()

        # Act
        result = await widget_service.delete(widget_id, admin_id, is_admin=True)

        # Assert
        assert result is not None
        mock_db.widgets.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_database_error(self, widget_service, mock_db, sample_widget_doc, mock_dashboard_doc):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        widget_id = "507f1f77bcf86cd799439011"
        mock_db.widgets.find_one = AsyncMock(return_value=sample_widget_doc)
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_db.widgets.delete_one = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.delete(widget_id, "user123")

        assert "Failed to delete widget" in str(exc_info.value.detail)


# ==================== Tests for count ====================


class TestCount:
    """Tests for counting widgets"""

    @pytest.mark.asyncio
    async def test_count_success(self, widget_service, mock_db):
        """POSITIVE: Should return correct count of widgets"""
        # Arrange
        expected_count = 42
        mock_db.widgets.count_documents = AsyncMock(return_value=expected_count)

        # Act
        result = await widget_service.count()

        # Assert
        assert result == expected_count
        mock_db.widgets.count_documents.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_count_with_dashboard_filter(self, widget_service, mock_db):
        """POSITIVE: Should count widgets filtered by dashboard"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        expected_count = 5
        mock_db.widgets.count_documents = AsyncMock(return_value=expected_count)

        # Act
        result = await widget_service.count(dashboard_id=dashboard_id)

        # Assert
        assert result == expected_count
        mock_db.widgets.count_documents.assert_called_once_with({"dashboard_id": dashboard_id})

    @pytest.mark.asyncio
    async def test_count_zero(self, widget_service, mock_db):
        """POSITIVE: Should return 0 when no widgets exist"""
        # Arrange
        mock_db.widgets.count_documents = AsyncMock(return_value=0)

        # Act
        result = await widget_service.count()

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_database_error(self, widget_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on database error"""
        # Arrange
        mock_db.widgets.count_documents = AsyncMock(side_effect=Exception("Connection error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.count()

        assert "Failed to count widgets" in str(exc_info.value.detail)


# ==================== Tests for ensure_indexes ====================


class TestEnsureIndexes:
    """Tests for index creation"""

    @pytest.mark.asyncio
    async def test_ensure_indexes_success(self, widget_service, mock_db):
        """POSITIVE: Should create indexes successfully"""
        # Arrange
        mock_db.widgets.create_index = AsyncMock()

        # Act
        await widget_service.ensure_indexes()

        # Assert
        mock_db.widgets.create_index.assert_called_once_with("dashboard_id")

    @pytest.mark.asyncio
    async def test_ensure_indexes_failure(self, widget_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on index creation failure"""
        # Arrange
        mock_db.widgets.create_index = AsyncMock(side_effect=Exception("Index error"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.ensure_indexes()

        assert "Failed to create indexes" in str(exc_info.value.detail)


# ==================== Tests for seed_initial ====================


class TestSeedInitial:
    """Tests for initial data seeding"""

    @pytest.mark.asyncio
    async def test_seed_initial_when_empty(self, widget_service, mock_db):
        """POSITIVE: Should seed initial widgets when dashboard has no widgets"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        mock_db.widgets.count_documents = AsyncMock(return_value=0)
        mock_db.widgets.insert_many = AsyncMock()

        # Act
        await widget_service.seed_initial(dashboard_id)

        # Assert
        mock_db.widgets.insert_many.assert_called_once()
        inserted_data = mock_db.widgets.insert_many.call_args[0][0]
        assert len(inserted_data) == 2
        assert inserted_data[0]["metric_type"] == "BPM"
        assert inserted_data[1]["metric_type"] == "ENERGY"

    @pytest.mark.asyncio
    async def test_seed_initial_skip_when_not_empty(self, widget_service, mock_db):
        """POSITIVE: Should skip seeding when widgets already exist"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        mock_db.widgets.count_documents = AsyncMock(return_value=5)
        mock_db.widgets.insert_many = AsyncMock()

        # Act
        await widget_service.seed_initial(dashboard_id)

        # Assert
        mock_db.widgets.insert_many.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_initial_database_error(self, widget_service, mock_db):
        """NEGATIVE: Should raise DatabaseException on seeding failure"""
        # Arrange
        dashboard_id = "507f191e810c19729de860ea"
        mock_db.widgets.count_documents = AsyncMock(return_value=0)
        mock_db.widgets.insert_many = AsyncMock(side_effect=Exception("Insert failed"))

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await widget_service.seed_initial(dashboard_id)

        assert "Failed to seed widgets" in str(exc_info.value.detail)


# ==================== Tests for get_by_dashboard ====================


class TestGetByDashboard:
    """Tests for getting widgets by dashboard"""

    @pytest.mark.asyncio
    async def test_get_by_dashboard_success(
        self,
        widget_service,
        mock_db,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Should return widgets for dashboard"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        user_id = "user123"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_widget_doc.copy()])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        result = await widget_service.get_by_dashboard(dashboard_id, user_id)

        # Assert
        assert len(result) >= 1
        mock_db.dashboards.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_dashboard_user_doesnt_own(self, widget_service, mock_db, mock_dashboard_doc):
        """NEGATIVE: Should raise BadRequestException when user doesn't own dashboard"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        different_user = "other_user"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)

        # Act & Assert
        with pytest.raises(BadRequestException) as exc_info:
            await widget_service.get_by_dashboard(dashboard_id, different_user)

        assert "don't have access" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_get_by_dashboard_admin_can_access_any(
        self,
        widget_service,
        mock_db,
        sample_widget_doc,
        mock_dashboard_doc
    ):
        """POSITIVE: Admin should access any dashboard's widgets"""
        # Arrange
        dashboard_id = str(mock_dashboard_doc["_id"])
        admin_id = "admin123"
        mock_db.dashboards.find_one = AsyncMock(return_value=mock_dashboard_doc)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[sample_widget_doc.copy()])
        mock_db.widgets.find.return_value = mock_cursor

        # Act
        result = await widget_service.get_by_dashboard(dashboard_id, admin_id, is_admin=True)

        # Assert
        assert result is not None
