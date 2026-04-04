import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


# ── helpers ──────────────────────────────────────────────────────────────────

async def create_system(client) -> str:
    """Create a system and return its id."""
    payload = {
        "name": "Test System",
        "description": "A test system for deployment tests",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "serial_number": str(uuid4()),
        "properties": {},
        "media_links": [],
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 201, f"System creation failed: {response.text}"
    return response.json()["id"]


def deployment_payload(**overrides) -> dict:
    """Return a valid deployment payload, with optional field overrides."""
    base = {
        "name": "Test Deployment",
        "description": "A test deployment",
        "deployment_type": "LABORATORY",
        "location": "Lab room 1",
        "properties": {"key": "value"},
    }
    base.update(overrides)
    return base


# ── creation ─────────────────────────────────────────────────────────────────

async def test_create_deployment(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Deployment"
    assert data["deployment_type"] == "LABORATORY"
    assert data["system_id"] == system_id


async def test_create_deployment_without_system_id(client):
    """system_id is required as a query param — omitting it should fail."""
    response = await client.post("/api/v1/deployments/", json=deployment_payload())
    assert response.status_code == 422


async def test_create_deployment_with_nonexistent_system_id(client):
    response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": str(uuid4())},
        json=deployment_payload(),
    )
    assert response.status_code == 404  # system not found


async def test_create_deployment_invalid_type(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(deployment_type="INVALID_TYPE"),
    )
    assert response.status_code == 422


async def test_create_deployment_missing_name(client):
    system_id = await create_system(client)
    payload = deployment_payload()
    payload.pop("name")
    response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=payload,
    )
    assert response.status_code == 422


async def test_create_deployment_all_types(client):
    """Every valid DeploymentType should be accepted."""
    valid_types = ["FIELD", "LABORATORY", "MOBILE", "FIXED", "TEMPORARY", "PERMANENT", "VIRTUAL", "CUSTOM"]
    system_id = await create_system(client)
    for dtype in valid_types:
        response = await client.post(
            "/api/v1/deployments/",
            params={"system_id": system_id},
            json=deployment_payload(name=f"Deployment {dtype}", deployment_type=dtype),
        )
        assert response.status_code == 201, f"Failed for type {dtype}: {response.text}"


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_deployment(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/deployments/{deployment_id}")
    assert response.status_code == 200
    assert response.json()["id"] == deployment_id


async def test_get_nonexistent_deployment(client):
    response = await client.get(f"/api/v1/deployments/{uuid4()}")
    assert response.status_code == 404


async def test_get_deployment_invalid_uuid(client):
    response = await client.get("/api/v1/deployments/not-a-uuid")
    assert response.status_code == 422


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_deployment(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/deployments/{deployment_id}",
        json={"name": "Updated Deployment Name"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Deployment Name"


async def test_partial_update_deployment(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    # Only update description — other fields should remain unchanged
    update_response = await client.put(
        f"/api/v1/deployments/{deployment_id}",
        json={"description": "Only description updated"},
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["description"] == "Only description updated"
    assert data["name"] == "Test Deployment"  # unchanged


async def test_update_deployment_invalid_type(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/deployments/{deployment_id}",
        json={"deployment_type": "UNSUPPORTED_TYPE"},
    )
    assert update_response.status_code == 422


async def test_update_nonexistent_deployment(client):
    response = await client.put(
        f"/api/v1/deployments/{uuid4()}",
        json={"name": "Ghost Update"},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_deployment(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/deployments/{deployment_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/deployments/{deployment_id}")
    assert get_response.status_code == 404


async def test_delete_deployment_twice(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    deployment_id = create_response.json()["id"]

    await client.delete(f"/api/v1/deployments/{deployment_id}")
    second_delete = await client.delete(f"/api/v1/deployments/{deployment_id}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_deployment(client):
    response = await client.delete(f"/api/v1/deployments/{uuid4()}")
    assert response.status_code == 404


# ── cascade / relational ──────────────────────────────────────────────────────

async def test_deployment_linked_to_correct_system(client):
    system_id = await create_system(client)
    create_response = await client.post(
        "/api/v1/deployments/",
        params={"system_id": system_id},
        json=deployment_payload(),
    )
    assert create_response.status_code == 201
    assert create_response.json()["system_id"] == system_id


async def test_multiple_deployments_same_system(client):
    """A system can have multiple deployments."""
    system_id = await create_system(client)
    for i in range(3):
        response = await client.post(
            "/api/v1/deployments/",
            params={"system_id": system_id},
            json=deployment_payload(name=f"Deployment {i}"),
        )
        assert response.status_code == 201


async def test_create_deployments_concurrently(client):
    system_id = await create_system(client)

    async def create(i):
        response = await client.post(
            "/api/v1/deployments/",
            params={"system_id": system_id},
            json=deployment_payload(name=f"Concurrent Deployment {i}"),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(5)])