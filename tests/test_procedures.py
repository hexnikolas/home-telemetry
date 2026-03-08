import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

def procedure_payload(**overrides) -> dict:
    """Return a valid procedure payload with optional field overrides."""
    base = {
        "name": "Test Procedure",
        "description": "A test procedure",
        "procedure_type": "DATA_COLLECTION",
        "reference": "https://example.com/procedure/123",
        "steps": ["Step 1: Initialize", "Step 2: Collect", "Step 3: Process"],
        "properties": {"key": "value"},
    }
    base.update(overrides)
    return base


async def create_procedure(client, **overrides) -> dict:
    """Create a procedure and return the response JSON."""
    response = await client.post("/api/v1/procedures/", json=procedure_payload(**overrides))
    assert response.status_code == 201, f"Procedure creation failed: {response.text}"
    return response.json()


# ── creation ──────────────────────────────────────────────────────────────────

async def test_create_procedure(client):
    response = await client.post("/api/v1/procedures/", json=procedure_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Procedure"
    assert data["procedure_type"] == "DATA_COLLECTION"
    assert data["steps"] == ["Step 1: Initialize", "Step 2: Collect", "Step 3: Process"]


async def test_create_procedure_minimal(client):
    """Only required fields — optional fields should default to None."""
    payload = {
        "name": "Minimal Procedure",
        "procedure_type": "MAINTENANCE",
    }
    response = await client.post("/api/v1/procedures/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Procedure"
    assert data["description"] is None
    assert data["reference"] is None
    assert data["steps"] == []
    assert data["properties"] is None


async def test_create_procedure_missing_name(client):
    payload = procedure_payload()
    payload.pop("name")
    response = await client.post("/api/v1/procedures/", json=payload)
    assert response.status_code == 422


async def test_create_procedure_missing_type(client):
    payload = procedure_payload()
    payload.pop("procedure_type")
    response = await client.post("/api/v1/procedures/", json=payload)
    assert response.status_code == 422


async def test_create_procedure_invalid_type(client):
    response = await client.post(
        "/api/v1/procedures/",
        json=procedure_payload(procedure_type="INVALID_TYPE"),
    )
    assert response.status_code == 422


async def test_create_procedure_all_types(client):
    """Every valid ProcedureType should be accepted."""
    valid_types = [
        "DATA_COLLECTION", "DATA_PROCESSING", "SENSOR_CALIBRATION",
        "ACTUATOR_OPERATION", "MAINTENANCE", "SHUTDOWN",
        "STARTUP", "ALGORITHM_EXECUTION", "USER_DEFINED",
    ]
    for ptype in valid_types:
        response = await client.post(
            "/api/v1/procedures/",
            json=procedure_payload(name=f"Procedure {ptype}", procedure_type=ptype),
        )
        assert response.status_code == 201, f"Failed for type {ptype}: {response.text}"


async def test_create_procedure_with_empty_steps(client):
    response = await client.post(
        "/api/v1/procedures/",
        json=procedure_payload(steps=[]),
    )
    assert response.status_code == 201
    assert response.json()["steps"] == []


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_procedure(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    response = await client.get(f"/api/v1/procedures/{procedure_id}")
    assert response.status_code == 200
    assert response.json()["id"] == procedure_id


async def test_get_procedure_data_integrity(client):
    """All fields should round-trip correctly."""
    created = await create_procedure(client)
    fetched = await client.get(f"/api/v1/procedures/{created['id']}")
    data = fetched.json()

    assert data["name"] == "Test Procedure"
    assert data["procedure_type"] == "DATA_COLLECTION"
    assert data["reference"] == "https://example.com/procedure/123"
    assert data["steps"] == ["Step 1: Initialize", "Step 2: Collect", "Step 3: Process"]
    assert data["properties"] == {"key": "value"}


async def test_get_nonexistent_procedure(client):
    response = await client.get(f"/api/v1/procedures/{uuid4()}")
    assert response.status_code == 404


async def test_get_procedure_invalid_uuid(client):
    response = await client.get("/api/v1/procedures/not-a-uuid")
    assert response.status_code == 422


async def test_list_procedures(client):
    # Create a couple so the list is non-empty
    await create_procedure(client, name="List Procedure 1")
    await create_procedure(client, name="List Procedure 2")

    response = await client.get("/api/v1/procedures/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


async def test_list_procedures_pagination(client):
    for i in range(5):
        await create_procedure(client, name=f"Paginated Procedure {i}")

    response_limit = await client.get("/api/v1/procedures/?limit=2&offset=0")
    assert response_limit.status_code == 200
    assert len(response_limit.json()) == 2

    response_offset = await client.get("/api/v1/procedures/?limit=2&offset=2")
    assert response_offset.status_code == 200
    # IDs should differ between pages
    ids_page1 = {p["id"] for p in response_limit.json()}
    ids_page2 = {p["id"] for p in response_offset.json()}
    assert ids_page1.isdisjoint(ids_page2)


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_procedure(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    response = await client.put(
        f"/api/v1/procedures/{procedure_id}",
        json={"name": "Updated Procedure Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Procedure Name"


async def test_partial_update_procedure(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    response = await client.put(
        f"/api/v1/procedures/{procedure_id}",
        json={"description": "Only description updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Only description updated"
    assert data["name"] == "Test Procedure"  # unchanged
    assert data["procedure_type"] == "DATA_COLLECTION"  # unchanged


async def test_update_procedure_steps(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    new_steps = ["New Step 1", "New Step 2"]
    response = await client.put(
        f"/api/v1/procedures/{procedure_id}",
        json={"steps": new_steps},
    )
    assert response.status_code == 200
    assert response.json()["steps"] == new_steps


async def test_update_procedure_invalid_type(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    response = await client.put(
        f"/api/v1/procedures/{procedure_id}",
        json={"procedure_type": "UNSUPPORTED_TYPE"},
    )
    assert response.status_code == 422


async def test_update_nonexistent_procedure(client):
    response = await client.put(
        f"/api/v1/procedures/{uuid4()}",
        json={"name": "Ghost Update"},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_procedure(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    delete_response = await client.delete(f"/api/v1/procedures/{procedure_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/procedures/{procedure_id}")
    assert get_response.status_code == 404


async def test_delete_procedure_twice(client):
    created = await create_procedure(client)
    procedure_id = created["id"]

    await client.delete(f"/api/v1/procedures/{procedure_id}")
    second_delete = await client.delete(f"/api/v1/procedures/{procedure_id}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_procedure(client):
    response = await client.delete(f"/api/v1/procedures/{uuid4()}")
    assert response.status_code == 404


# ── concurrency ───────────────────────────────────────────────────────────────

async def test_create_procedures_concurrently(client):
    async def create(i):
        response = await client.post(
            "/api/v1/procedures/",
            json=procedure_payload(name=f"Concurrent Procedure {i}"),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(5)])