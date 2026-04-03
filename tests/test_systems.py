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


async def test_get_system_status(client):
    # Create system
    payload = {
        "name": "Status Test System",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "serial_number": str(uuid4()),
    }
    system_response = await client.post("/api/v1/systems/", json=payload)
    system_id = system_response.json()["id"]

    # 1. New system with no datastreams should return 404 per implementation
    status_response = await client.get(f"/api/v1/systems/{system_id}/status")
    assert status_response.status_code == 404
    assert "No datastreams found" in status_response.json()["detail"]

    # Create datastream
    ds_payload = {
        "name": "Status DS",
        "system_id": system_id,
        "is_gps_enabled": False,
        "observation_result_type": "FLOAT",
    }
    ds_response = await client.post("/api/v1/datastreams/", json=ds_payload)
    ds_id = ds_response.json()["id"]

    # 2. System with datastream but no observations should return 404 per implementation
    status_response = await client.get(f"/api/v1/systems/{system_id}/status")
    assert status_response.status_code == 404
    assert "No observations found" in status_response.json()["detail"]

    # Create observation (current time)
    from datetime import datetime, timezone
    obs_payload = {
        "datastream_id": ds_id,
        "result_time": datetime.now(timezone.utc).isoformat(),
        "result_numeric": 25.0
    }
    await client.post("/api/v1/observations/", json=obs_payload)

    # 3. Status should now be True
    status_response = await client.get(f"/api/v1/systems/{system_id}/status?online_within_seconds=60")
    assert status_response.status_code == 200
    assert status_response.json() is True

    # Sleep for 5 seconds
    await asyncio.sleep(5)

    # 4. Status should be False if we check within a 4 second window
    status_response = await client.get(f"/api/v1/systems/{system_id}/status?online_within_seconds=4")
    assert status_response.status_code == 200
    assert status_response.json() is False


async def test_list_systems_with_keyword_filter(client):
    # Create systems with different names and descriptions
    system_1 = {
        "name": "Weather Station Indoor",
        "description": "Indoor temperature and humidity sensor",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "serial_number": "WS-001"
    }
    response_1 = await client.post("/api/v1/systems/", json=system_1)
    assert response_1.status_code == 201

    system_2 = {
        "name": "Power Socket Plug",
        "description": "Smart plug measuring energy consumption",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "serial_number": "PSP-001"
    }
    response_2 = await client.post("/api/v1/systems/", json=system_2)
    assert response_2.status_code == 201

    system_3 = {
        "name": "Outdoor Weather Monitor",
        "description": "Monitors outdoor environmental conditions",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "serial_number": "OWM-001"
    }
    response_3 = await client.post("/api/v1/systems/", json=system_3)
    assert response_3.status_code == 201

    # Test single keyword matching in name
    response = await client.get("/api/v1/systems/?q=weather&limit=100")
    assert response.status_code == 200
    systems = response.json()
    system_names = [s["name"] for s in systems]
    assert "Weather Station Indoor" in system_names
    assert "Outdoor Weather Monitor" in system_names
    assert "Power Socket Plug" not in system_names

    # Test keyword matching in description
    response = await client.get("/api/v1/systems/?q=energy&limit=100")
    assert response.status_code == 200
    systems = response.json()
    system_names = [s["name"] for s in systems]
    assert "Power Socket Plug" in system_names
    assert len(systems) == 1

    # Test multiple keywords (OR logic)
    response = await client.get("/api/v1/systems/?q=weather,energy&limit=100")
    assert response.status_code == 200
    systems = response.json()
    system_names = [s["name"] for s in systems]
    assert "Weather Station Indoor" in system_names
    assert "Outdoor Weather Monitor" in system_names
    assert "Power Socket Plug" in system_names
    assert len(systems) == 3

    # Test keyword with no matches
    response = await client.get("/api/v1/systems/?q=nonexistent&limit=100")
    assert response.status_code == 404
