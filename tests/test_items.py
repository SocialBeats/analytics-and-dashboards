"""
Tests for Item endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient, sample_item_data):
    """Test creating a new item"""
    response = await client.post("/api/v1/analytics/items", json=sample_item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_item_data["title"]
    assert data["description"] == sample_item_data["description"]
    assert data["completed"] == sample_item_data["completed"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_items(client: AsyncClient, sample_item_data):
    """Test retrieving all items"""
    # Create an item first
    await client.post("/api/v1/analytics/items", json=sample_item_data)

    # Get all items
    response = await client.get("/api/v1/analytics/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_get_item_by_id(client: AsyncClient, sample_item_data):
    """Test retrieving a specific item by ID"""
    # Create an item
    create_response = await client.post("/api/v1/analytics/items", json=sample_item_data)
    item_id = create_response.json()["id"]

    # Get the item
    response = await client.get(f"/api/v1/analytics/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["title"] == sample_item_data["title"]


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """Test retrieving a non-existent item"""
    response = await client.get("/api/v1/analytics/items/507f1f77bcf86cd799439011")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_item(client: AsyncClient, sample_item_data):
    """Test updating an existing item"""
    # Create an item
    create_response = await client.post("/api/v1/analytics/items", json=sample_item_data)
    item_id = create_response.json()["id"]

    # Update the item
    update_data = {"title": "Updated Title", "completed": True}
    response = await client.put(f"/api/v1/analytics/items/{item_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["completed"] is True
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient, sample_item_data):
    """Test deleting an item"""
    # Create an item
    create_response = await client.post("/api/v1/analytics/items", json=sample_item_data)
    item_id = create_response.json()["id"]

    # Delete the item
    response = await client.delete(f"/api/v1/analytics/items/{item_id}")
    assert response.status_code == 200

    # Verify item is deleted
    get_response = await client.get(f"/api/v1/analytics/items/{item_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_not_found(client: AsyncClient):
    """Test deleting a non-existent item"""
    response = await client.delete("/api/v1/analytics/items/507f1f77bcf86cd799439011")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_item_validation(client: AsyncClient):
    """Test item creation with invalid data"""
    invalid_data = {"description": "Missing title"}
    response = await client.post("/api/v1/analytics/items", json=invalid_data)
    assert response.status_code == 422
