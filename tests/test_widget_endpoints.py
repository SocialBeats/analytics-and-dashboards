"""
Integration tests for Widget endpoints

Tests the full API endpoints including routing, authentication, and database operations.
Uses real database with test data isolation.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import patch
from httpx import AsyncClient
from bson import ObjectId

from main import app
from app.database.config import get_db


@pytest_asyncio.fixture
async def db_with_dashboard_and_widget(test_db):
    """Create a test dashboard and widget in the database"""
    # Create dashboard first
    dashboard_doc = {
        "_id": ObjectId(),
        "owner_id": "user123",
        "beat_id": "beat123",
        "name": "Test Dashboard for Widgets",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    dashboard_result = await test_db.dashboards.insert_one(dashboard_doc)
    dashboard_doc["_id"] = dashboard_result.inserted_id

    # Create widget
    widget_doc = {
        "_id": ObjectId(),
        "dashboard_id": str(dashboard_doc["_id"]),
        "metric_type": "BPM",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    widget_result = await test_db.widgets.insert_one(widget_doc)
    widget_doc["_id"] = widget_result.inserted_id

    yield test_db, dashboard_doc, widget_doc

    # Cleanup
    await test_db.widgets.delete_many({})
    await test_db.dashboards.delete_many({})


@pytest_asyncio.fixture
async def db_with_multiple_widgets(test_db):
    """Create multiple test widgets for different dashboards"""
    # Create dashboards
    dashboard1 = {
        "_id": ObjectId(),
        "owner_id": "user123",
        "beat_id": "beat123",
        "name": "User Dashboard 1",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    dashboard2 = {
        "_id": ObjectId(),
        "owner_id": "other_user",
        "beat_id": "beat456",
        "name": "Other User Dashboard",
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    await test_db.dashboards.insert_many([dashboard1, dashboard2])

    # Create widgets
    widgets = [
        {
            "_id": ObjectId(),
            "dashboard_id": str(dashboard1["_id"]),
            "metric_type": "BPM",
            "created_at": datetime.utcnow(),
            "updated_at": None
        },
        {
            "_id": ObjectId(),
            "dashboard_id": str(dashboard1["_id"]),
            "metric_type": "ENERGY",
            "created_at": datetime.utcnow(),
            "updated_at": None
        },
        {
            "_id": ObjectId(),
            "dashboard_id": str(dashboard2["_id"]),
            "metric_type": "BPM",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
    ]
    await test_db.widgets.insert_many(widgets)

    yield test_db, dashboard1, dashboard2, widgets

    # Cleanup
    await test_db.widgets.delete_many({})
    await test_db.dashboards.delete_many({})


@pytest_asyncio.fixture
async def client_with_test_db(client, test_db):
    """Override the get_db dependency to use test database"""
    async def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    yield client
    app.dependency_overrides.clear()


# ==================== Tests for GET /analytics/widgets ====================


class TestListWidgets:
    """Tests for listing widgets endpoint"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_list_widgets_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_regular
    ):
        """POSITIVE: Should list all widgets"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets

        # Act
        response = await client_with_test_db.get(
            "/api/v1/analytics/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_list_widgets_filtered_by_dashboard(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_regular
    ):
        """POSITIVE: Should filter widgets by dashboard_id"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets
        dashboard_id = str(dashboard1["_id"])

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/widgets?dashboardId={dashboard_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # Dashboard1 has 2 widgets

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_list_widgets_with_pagination(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_regular
    ):
        """POSITIVE: Pagination should work correctly"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets

        # Act
        response = await client_with_test_db.get(
            "/api/v1/analytics/widgets?skip=0&limit=2",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_list_widgets_empty(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular
    ):
        """POSITIVE: Should return empty list when no widgets exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        await test_db.widgets.delete_many({})

        # Act
        response = await client_with_test_db.get(
            "/api/v1/analytics/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ==================== Tests for GET /analytics/widgets/{widget_id} ====================


class TestGetWidget:
    """Tests for getting a specific widget"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_widget_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_regular
    ):
        """POSITIVE: Should return widget by ID"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/widgets/{widget_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == widget_id
        assert data["metricType"] == widget["metric_type"]

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_widget_not_found(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular
    ):
        """NEGATIVE: Should return 404 when widget doesn't exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        non_existent_id = str(ObjectId())

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/widgets/{non_existent_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_widget_invalid_id(
        self,
        mock_auth,
        client_with_test_db,
        mock_user_regular
    ):
        """NEGATIVE: Should return 400 for invalid ID format"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        invalid_id = "invalid_id_format"

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/widgets/{invalid_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid widget ID format" in response.json()["detail"]


# ==================== Tests for POST /analytics/widgets ====================


class TestCreateWidget:
    """Tests for creating widgets"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_create_widget_success(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_widget_data
    ):
        """POSITIVE: Should create widget successfully"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        # Create dashboard first
        dashboard_doc = {
            "_id": ObjectId(sample_widget_data["dashboardId"]),
            "owner_id": "user123",
            "beat_id": "beat123",
            "name": "Test Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)

        # Act
        response = await client_with_test_db.post(
            "/api/v1/analytics/widgets",
            json=sample_widget_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["metricType"] == sample_widget_data["metricType"]

        # Cleanup
        await test_db.dashboards.delete_many({})
        await test_db.widgets.delete_many({})

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_create_widget_admin(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_admin,
        sample_widget_data
    ):
        """POSITIVE: Admin should be able to create widget on any dashboard"""
        # Arrange
        mock_auth.return_value = mock_user_admin
        # Create dashboard owned by different user
        dashboard_doc = {
            "_id": ObjectId(sample_widget_data["dashboardId"]),
            "owner_id": "other_user",
            "beat_id": "beat123",
            "name": "Other User Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)

        # Act
        response = await client_with_test_db.post(
            "/api/v1/analytics/widgets",
            json=sample_widget_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "admin123",
                "x-roles": '["admin", "user"]'
            }
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["metricType"] == sample_widget_data["metricType"]

        # Cleanup
        await test_db.dashboards.delete_many({})
        await test_db.widgets.delete_many({})

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_create_widget_dashboard_not_found(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_widget_data
    ):
        """NEGATIVE: Should return 404 when dashboard doesn't exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        await test_db.dashboards.delete_many({})

        # Act
        response = await client_with_test_db.post(
            "/api/v1/analytics/widgets",
            json=sample_widget_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 404
        assert "Dashboard" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_create_widget_user_doesnt_own_dashboard(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_widget_data
    ):
        """NEGATIVE: Should return 400 when user doesn't own dashboard"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        # Create dashboard owned by different user
        dashboard_doc = {
            "_id": ObjectId(sample_widget_data["dashboardId"]),
            "owner_id": "other_user",
            "beat_id": "beat123",
            "name": "Other User Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)

        # Act
        response = await client_with_test_db.post(
            "/api/v1/analytics/widgets",
            json=sample_widget_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 400
        assert "don't have access" in response.json()["detail"].lower()

        # Cleanup
        await test_db.dashboards.delete_many({})

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_create_widget_missing_fields(
        self,
        mock_auth,
        client_with_test_db,
        mock_user_regular
    ):
        """NEGATIVE: Should return 422 for missing required fields"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        incomplete_data = {"metricType": "BPM"}  # Missing dashboardId

        # Act
        response = await client_with_test_db.post(
            "/api/v1/analytics/widgets",
            json=incomplete_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 422


# ==================== Tests for PUT /analytics/widgets/{widget_id} ====================


class TestUpdateWidget:
    """Tests for updating widgets"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_update_widget_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_regular,
        sample_widget_update_data
    ):
        """POSITIVE: Should update widget successfully"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.put(
            f"/api/v1/analytics/widgets/{widget_id}",
            json=sample_widget_update_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == widget_id
        assert data["metricType"] == sample_widget_update_data["metricType"]
        assert data["updatedAt"] is not None

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_update_widget_user_doesnt_own_dashboard(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        sample_widget_update_data
    ):
        """NEGATIVE: Should return 400 when user doesn't own dashboard"""
        # Arrange
        different_user = {
            "userId": "different_user",
            "username": "otheruser",
            "roles": ["user"]
        }
        mock_auth.return_value = different_user

        # Create dashboard owned by user123
        dashboard_doc = {
            "_id": ObjectId(),
            "owner_id": "user123",
            "beat_id": "beat123",
            "name": "User123 Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)

        # Create widget for that dashboard
        widget_doc = {
            "_id": ObjectId(),
            "dashboard_id": str(dashboard_doc["_id"]),
            "metric_type": "BPM",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.widgets.insert_one(widget_doc)
        widget_id = str(widget_doc["_id"])

        # Act
        response = await client_with_test_db.put(
            f"/api/v1/analytics/widgets/{widget_id}",
            json=sample_widget_update_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "different_user",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 400
        assert "don't have access" in response.json()["detail"].lower()

        # Cleanup
        await test_db.widgets.delete_many({})
        await test_db.dashboards.delete_many({})

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_update_widget_admin_can_update_any(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_admin,
        sample_widget_update_data
    ):
        """POSITIVE: Admin should be able to update any widget"""
        # Arrange
        mock_auth.return_value = mock_user_admin
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.put(
            f"/api/v1/analytics/widgets/{widget_id}",
            json=sample_widget_update_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "admin123",
                "x-roles": '["admin", "user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["metricType"] == sample_widget_update_data["metricType"]

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_update_widget_not_found(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular,
        sample_widget_update_data
    ):
        """NEGATIVE: Should return 404 when widget doesn't exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        non_existent_id = str(ObjectId())

        # Act
        response = await client_with_test_db.put(
            f"/api/v1/analytics/widgets/{non_existent_id}",
            json=sample_widget_update_data,
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_update_widget_empty_update(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_regular
    ):
        """POSITIVE: Should return unchanged widget for empty update"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.put(
            f"/api/v1/analytics/widgets/{widget_id}",
            json={},
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["metricType"] == widget["metric_type"]


# ==================== Tests for DELETE /analytics/widgets/{widget_id} ====================


class TestDeleteWidget:
    """Tests for deleting widgets"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_delete_widget_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_regular
    ):
        """POSITIVE: Should delete widget successfully"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.delete(
            f"/api/v1/analytics/widgets/{widget_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()

        # Verify widget was actually deleted
        deleted = await test_db.widgets.find_one({"_id": widget["_id"]})
        assert deleted is None

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_delete_widget_user_doesnt_own_dashboard(
        self,
        mock_auth,
        client_with_test_db,
        test_db
    ):
        """NEGATIVE: Should return 400 when user doesn't own dashboard"""
        # Arrange
        different_user = {
            "userId": "different_user",
            "username": "otheruser",
            "roles": ["user"]
        }
        mock_auth.return_value = different_user

        # Create dashboard owned by user123
        dashboard_doc = {
            "_id": ObjectId(),
            "owner_id": "user123",
            "beat_id": "beat123",
            "name": "User123 Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)

        # Create widget for that dashboard
        widget_doc = {
            "_id": ObjectId(),
            "dashboard_id": str(dashboard_doc["_id"]),
            "metric_type": "BPM",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.widgets.insert_one(widget_doc)
        widget_id = str(widget_doc["_id"])

        # Act
        response = await client_with_test_db.delete(
            f"/api/v1/analytics/widgets/{widget_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "different_user",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 400
        assert "don't have access" in response.json()["detail"].lower()

        # Verify widget was NOT deleted
        existing = await test_db.widgets.find_one({"_id": widget_doc["_id"]})
        assert existing is not None

        # Cleanup
        await test_db.widgets.delete_many({})
        await test_db.dashboards.delete_many({})

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_delete_widget_admin_can_delete_any(
        self,
        mock_auth,
        client_with_test_db,
        db_with_dashboard_and_widget,
        mock_user_admin
    ):
        """POSITIVE: Admin should be able to delete any widget"""
        # Arrange
        mock_auth.return_value = mock_user_admin
        test_db, dashboard, widget = db_with_dashboard_and_widget
        widget_id = str(widget["_id"])

        # Act
        response = await client_with_test_db.delete(
            f"/api/v1/analytics/widgets/{widget_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "admin123",
                "x-roles": '["admin", "user"]'
            }
        )

        # Assert
        assert response.status_code == 200

        # Verify widget was deleted
        deleted = await test_db.widgets.find_one({"_id": widget["_id"]})
        assert deleted is None

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_delete_widget_not_found(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular
    ):
        """NEGATIVE: Should return 404 when widget doesn't exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        non_existent_id = str(ObjectId())

        # Act
        response = await client_with_test_db.delete(
            f"/api/v1/analytics/widgets/{non_existent_id}",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ==================== Tests for GET /analytics/dashboards/{dashboard_id}/widgets ====================


class TestGetDashboardWidgets:
    """Tests for getting widgets by dashboard"""

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_dashboard_widgets_success(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_regular
    ):
        """POSITIVE: Should return all widgets for a dashboard"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets
        dashboard_id = str(dashboard1["_id"])

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/dashboards/{dashboard_id}/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # Dashboard1 has 2 widgets

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_dashboard_widgets_user_doesnt_own(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_regular
    ):
        """NEGATIVE: Should return 400 when user doesn't own dashboard"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets
        dashboard_id = str(dashboard2["_id"])  # Dashboard2 is owned by other_user

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/dashboards/{dashboard_id}/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 400
        assert "don't have access" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_dashboard_widgets_admin_can_access_any(
        self,
        mock_auth,
        client_with_test_db,
        db_with_multiple_widgets,
        mock_user_admin
    ):
        """POSITIVE: Admin should access any dashboard's widgets"""
        # Arrange
        mock_auth.return_value = mock_user_admin
        test_db, dashboard1, dashboard2, widgets = db_with_multiple_widgets
        dashboard_id = str(dashboard2["_id"])  # Dashboard2 is owned by other_user

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/dashboards/{dashboard_id}/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "admin123",
                "x-roles": '["admin", "user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_dashboard_widgets_dashboard_not_found(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular
    ):
        """NEGATIVE: Should return 404 when dashboard doesn't exist"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        non_existent_id = str(ObjectId())

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/dashboards/{non_existent_id}/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 404
        assert "Dashboard" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch('app.endpoints.widgets.get_current_user')
    async def test_get_dashboard_widgets_empty(
        self,
        mock_auth,
        client_with_test_db,
        test_db,
        mock_user_regular
    ):
        """POSITIVE: Should return empty list when dashboard has no widgets"""
        # Arrange
        mock_auth.return_value = mock_user_regular
        # Create dashboard without widgets
        dashboard_doc = {
            "_id": ObjectId(),
            "owner_id": "user123",
            "beat_id": "beat123",
            "name": "Empty Dashboard",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        await test_db.dashboards.insert_one(dashboard_doc)
        dashboard_id = str(dashboard_doc["_id"])

        # Act
        response = await client_with_test_db.get(
            f"/api/v1/analytics/dashboards/{dashboard_id}/widgets",
            headers={
                "x-gateway-authenticated": "true",
                "x-user-id": "user123",
                "x-roles": '["user"]'
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

        # Cleanup
        await test_db.dashboards.delete_many({})
