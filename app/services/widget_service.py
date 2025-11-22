"""
Widget service - Business logic for Widget operations
"""
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException
from app.schemas.widget import WidgetCreate, WidgetUpdate


class WidgetService:
    """Service class for Widget-related business logic"""
    
    MAX_GRID_WIDTH = 5  # Maximum grid width (5 columns)

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.widgets

    async def ensure_indexes(self):
        """Create necessary indexes for the widgets collection"""
        try:
            await self.collection.create_index("dashboard_id")
        except Exception as e:
            raise DatabaseException(f"Failed to create indexes: {str(e)}")

    async def seed_initial(self, dashboard_id: str):
        """
        Seed initial widgets for a dashboard if none exist
        
        Args:
            dashboard_id: Dashboard ID to seed widgets for
        """
        count = await self.collection.count_documents({"dashboard_id": dashboard_id})
        if count == 0:
            initial_widgets = [
                {
                    "dashboard_id": dashboard_id,
                    "metric_type": "BPM",
                    "created_at": datetime.utcnow(),
                    "updated_at": None
                },
                {
                    "dashboard_id": dashboard_id,
                    "metric_type": "ENERGY",
                    "created_at": datetime.utcnow(),
                    "updated_at": None
                }
            ]
            try:
                await self.collection.insert_many(initial_widgets)
            except Exception as e:
                raise DatabaseException(f"Failed to seed widgets: {str(e)}")

    @staticmethod
    def validate_object_id(widget_id: str) -> ObjectId:
        """
        Validate and convert string ID to ObjectId

        Args:
            widget_id: String representation of ObjectId

        Returns:
            ObjectId: Validated ObjectId

        Raises:
            BadRequestException: If ID is invalid
        """
        try:
            return ObjectId(widget_id)
        except InvalidId:
            raise BadRequestException(f"Invalid widget ID format: {widget_id}")


    @staticmethod
    def serialize_widget(widget: dict) -> dict:
        """
        Serialize MongoDB document to API response format

        Args:
            widget: MongoDB document

        Returns:
            Serialized widget dictionary
        """
        if widget and "_id" in widget:
            widget["id"] = str(widget.pop("_id"))
        return widget


    async def get_all(self, dashboard_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        Retrieve all widgets with optional filtering and pagination
        Widgets are sorted by position (row-major order)

        Args:
            dashboard_id: Optional dashboard ID filter
            skip: Number of widgets to skip
            limit: Maximum number of widgets to return

        Returns:
            List of widgets sorted by position
        """
        try:
            query = {}
            if dashboard_id:
                query["dashboard_id"] = dashboard_id

            cursor = self.collection.find(query).skip(skip).limit(limit)
            widgets = await cursor.to_list(length=limit)
            return [self.serialize_widget(widget) for widget in widgets]
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve widgets: {str(e)}")

    async def get_by_id(self, widget_id: str) -> dict:
        """
        Retrieve a single widget by ID

        Args:
            widget_id: Widget identifier

        Returns:
            Widget document

        Raises:
            NotFoundException: If widget not found
        """
        object_id = self.validate_object_id(widget_id)

        try:
            widget = await self.collection.find_one({"_id": object_id})
            if not widget:
                raise NotFoundException(resource="Widget", resource_id=widget_id)
            return self.serialize_widget(widget)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve widget: {str(e)}")

    async def create(self, widget_data: WidgetCreate) -> dict:
        """
        Create a new widget

        Args:
            widget_data: Widget creation data

        Returns:
            Created widget document
        """
        widget_dict = widget_data.model_dump(by_alias=False)

        try:
            widget_dict["created_at"] = datetime.utcnow()
            widget_dict["updated_at"] = None

            result = await self.collection.insert_one(widget_dict)
            created_widget = await self.collection.find_one({"_id": result.inserted_id})

            return self.serialize_widget(created_widget)
        except Exception as e:
            raise DatabaseException(f"Failed to create widget: {str(e)}")

    async def update(self, widget_id: str, widget_data: WidgetUpdate) -> dict:
        """
        Update an existing widget

        Args:
            widget_id: Widget identifier
            widget_data: Widget update data

        Returns:
            Updated widget document

        Raises:
            NotFoundException: If widget not found
        """
        object_id = self.validate_object_id(widget_id)

        # Check if widget exists
        existing_widget = await self.collection.find_one({"_id": object_id})
        if not existing_widget:
            raise NotFoundException(resource="Widget", resource_id=widget_id)

        try:
            # Prepare update data
            update_data = widget_data.model_dump(exclude_unset=True, by_alias=False)

            if not update_data:
                return self.serialize_widget(existing_widget)

            update_data["updated_at"] = datetime.utcnow()

            await self.collection.update_one({"_id": object_id}, {"$set": update_data})
            updated_widget = await self.collection.find_one({"_id": object_id})

            return self.serialize_widget(updated_widget)
        except (NotFoundException, BadRequestException):
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to update widget: {str(e)}")

    async def delete(self, widget_id: str) -> dict:
        """
        Delete a widget

        Args:
            widget_id: Widget identifier

        Returns:
            Success message

        Raises:
            NotFoundException: If widget not found
        """
        object_id = self.validate_object_id(widget_id)

        # Check if widget exists
        existing_widget = await self.collection.find_one({"_id": object_id})
        if not existing_widget:
            raise NotFoundException(resource="Widget", resource_id=widget_id)

        try:
            await self.collection.delete_one({"_id": object_id})
            return {"message": "Widget deleted successfully", "id": widget_id}
        except Exception as e:
            raise DatabaseException(f"Failed to delete widget: {str(e)}")

    async def count(self, dashboard_id: Optional[str] = None) -> int:
        """
        Count total number of widgets, optionally filtered by dashboard

        Args:
            dashboard_id: Optional dashboard ID filter

        Returns:
            Total count of widgets
        """
        try:
            query = {}
            if dashboard_id:
                query["dashboard_id"] = dashboard_id
            return await self.collection.count_documents(query)
        except Exception as e:
            raise DatabaseException(f"Failed to count widgets: {str(e)}")

    async def get_by_dashboard(self, dashboard_id: str) -> List[dict]:
        """
        Get all widgets for a specific dashboard, sorted by position

        Args:
            dashboard_id: Dashboard identifier

        Returns:
            List of widgets sorted by position
        """
        return await self.get_all(dashboard_id=dashboard_id, skip=0, limit=1000)