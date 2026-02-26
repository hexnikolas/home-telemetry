import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


async def test_create_system(client):
    payload = {
        "name": "Test System",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["system_type"] == payload["system_type"]


async def test_create_system_invalid_payload(client):
    payload = {
        "name": "",  # Invalid name
        "description": "A test system",
        "system_type": "INVALID_TYPE",  # Unsupported type
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 422  # Expecting validation error


async def test_create_duplicate_system(client):
    payload = {
        "name": "Duplicate System",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 201

    duplicate_response = await client.post("/api/v1/systems/", json=payload)
    assert duplicate_response.status_code == 400  # Expecting duplicate error


async def test_get_system(client):
    payload = {
        "name": "Test System",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    create_response = await client.post("/api/v1/systems/", json=payload)
    assert create_response.status_code == 201
    system_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/systems/{system_id}")
    assert response.status_code == 200
    assert response.json()["id"] == system_id


async def test_delete_non_existent_system(client):
    non_existent_id = str(uuid4())
    response = await client.delete(f"/api/v1/systems/{non_existent_id}")
    assert response.status_code == 404  # Not found


async def test_get_non_existent_system(client):
    non_existent_id = str(uuid4())
    response = await client.get(f"/api/v1/systems/{non_existent_id}")
    assert response.status_code == 404  # Not found


async def test_get_system_invalid_uuid(client):
    invalid_uuid = "not-a-uuid"
    response = await client.get(f"/api/v1/systems/{invalid_uuid}")
    assert response.status_code == 422  # Validation error


async def test_update_non_existent_system(client):
    non_existent_id = str(uuid4())
    update_payload = {
        "name": "Updated Name",
        "description": "Updated Description"
    }
    response = await client.put(f"/api/v1/systems/{non_existent_id}", json=update_payload)
    assert response.status_code == 404  # Not found


async def test_create_system_invalid_data_types(client):
    payload = {
        "name": "Invalid Data Type System",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": "not-a-boolean",  # Invalid data type
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 422  # Validation error


async def test_create_multiple_systems_concurrently(client):
    payload1 = {
        "name": "Concurrent System 1",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345-1",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }

    payload2 = {
        "name": "Concurrent System 2",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345-2",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }

    async def create_system(payload):
        response = await client.post("/api/v1/systems/", json=payload)
        assert response.status_code == 201

    await asyncio.gather(create_system(payload1), create_system(payload2))


async def test_delete_system_twice(client):
    payload = {
        "name": "System to Delete Twice",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    create_response = await client.post("/api/v1/systems/", json=payload)
    assert create_response.status_code == 201
    system_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/systems/{system_id}")
    assert delete_response.status_code == 204

    second_delete_response = await client.delete(f"/api/v1/systems/{system_id}")
    assert second_delete_response.status_code == 404  # Not found


async def test_partial_update_system(client):
    payload = {
        "name": "System to Partially Update",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    create_response = await client.post("/api/v1/systems/", json=payload)
    assert create_response.status_code == 201
    system_id = create_response.json()["id"]

    update_payload = {"name": "Partially Updated Name"}  # Partial update
    update_response = await client.put(f"/api/v1/systems/{system_id}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Partially Updated Name"


async def test_update_system_invalid_data(client):
    payload = {
        "name": "System to Update Invalid",
        "description": "A test system",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": True,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": "12345",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image"]
    }
    create_response = await client.post("/api/v1/systems/", json=payload)
    assert create_response.status_code == 201
    system_id = create_response.json()["id"]

    update_payload = {"system_type": "UNSUPPORTED_TYPE"}  # Invalid data
    update_response = await client.put(f"/api/v1/systems/{system_id}", json=update_payload)
    assert update_response.status_code == 422  # Validation error