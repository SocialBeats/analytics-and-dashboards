"""
Item service - Business logic for Item operations
"""
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """Service class for Item-related business logic"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.items

    @staticmethod
    def validate_object_id(item_id: str) -> ObjectId:
        """
        Validate and convert string ID to ObjectId

        Args:
            item_id: String representation of ObjectId

        Returns:
            ObjectId: Validated ObjectId

        Raises:
            BadRequestException: If ID is invalid
        """
        try:
            return ObjectId(item_id)
        except InvalidId:
            raise BadRequestException(f"Invalid item ID format: {item_id}")

    @staticmethod
    def serialize_item(item: dict) -> dict:
        """
        Serialize MongoDB document to API response format

        Args:
            item: MongoDB document

        Returns:
            Serialized item dictionary
        """
        if item and "_id" in item:
            item["id"] = str(item.pop("_id"))
        return item

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        Retrieve all items with pagination

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of items
        """
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            items = await cursor.to_list(length=limit)
            return [self.serialize_item(item) for item in items]
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve items: {str(e)}")

    async def get_by_id(self, item_id: str) -> dict:
        """
        Retrieve a single item by ID

        Args:
            item_id: Item identifier

        Returns:
            Item document

        Raises:
            NotFoundException: If item not found
        """
        object_id = self.validate_object_id(item_id)

        try:
            item = await self.collection.find_one({"_id": object_id})
            if not item:
                raise NotFoundException(resource="Item", resource_id=item_id)
            return self.serialize_item(item)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve item: {str(e)}")

    async def create(self, item_data: ItemCreate) -> dict:
        """
        Create a new item

        Args:
            item_data: Item creation data

        Returns:
            Created item document
        """
        try:
            item_dict = item_data.model_dump()
            item_dict["created_at"] = datetime.utcnow()
            item_dict["updated_at"] = None

            result = await self.collection.insert_one(item_dict)
            created_item = await self.collection.find_one({"_id": result.inserted_id})

            return self.serialize_item(created_item)
        except Exception as e:
            raise DatabaseException(f"Failed to create item: {str(e)}")

    async def update(self, item_id: str, item_data: ItemUpdate) -> dict:
        """
        Update an existing item

        Args:
            item_id: Item identifier
            item_data: Item update data

        Returns:
            Updated item document

        Raises:
            NotFoundException: If item not found
        """
        object_id = self.validate_object_id(item_id)

        # Check if item exists
        existing_item = await self.collection.find_one({"_id": object_id})
        if not existing_item:
            raise NotFoundException(resource="Item", resource_id=item_id)

        try:
            # Prepare update data
            update_data = item_data.model_dump(exclude_unset=True)

            if not update_data:
                # No fields to update, return existing item
                return self.serialize_item(existing_item)

            update_data["updated_at"] = datetime.utcnow()

            await self.collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )

            updated_item = await self.collection.find_one({"_id": object_id})
            return self.serialize_item(updated_item)
        except Exception as e:
            raise DatabaseException(f"Failed to update item: {str(e)}")

    async def delete(self, item_id: str) -> dict:
        """
        Delete an item

        Args:
            item_id: Item identifier

        Returns:
            Success message

        Raises:
            NotFoundException: If item not found
        """
        object_id = self.validate_object_id(item_id)

        # Check if item exists
        existing_item = await self.collection.find_one({"_id": object_id})
        if not existing_item:
            raise NotFoundException(resource="Item", resource_id=item_id)

        try:
            await self.collection.delete_one({"_id": object_id})
            return {"message": "Item deleted successfully", "id": item_id}
        except Exception as e:
            raise DatabaseException(f"Failed to delete item: {str(e)}")

    async def count(self) -> int:
        """
        Count total number of items

        Returns:
            Total count of items
        """
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            raise DatabaseException(f"Failed to count items: {str(e)}")
