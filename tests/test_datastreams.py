import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

async def create_system(client) -> str:
    payload = {
        "name": "Test System",
        "system_type": "SENSOR",
        "external_id": str(uuid4()),
        "is_mobile": False,
        "is_gps_enabled": False,
        "serial_number": str(uuid4()),
    }
    response = await client.post("/api/v1/systems/", json=payload)
    assert response.status_code == 201, f"System creation failed: {response.text}"
    return response.json()["id"]


async def create_deployment(client, system_id: str) -> str:
    payload = {
        "name": "Test Deployment",
        "deployment_type": "LABORATORY",
    }
    response = await client.post("/api/v1/deployments/", params={"system_id": system_id}, json=payload)
    assert response.status_code == 201, f"Deployment creation failed: {response.text}"
    return response.json()["id"]


async def create_procedure(client) -> str:
    payload = {
        "name": "Test Procedure",
        "procedure_type": "DATA_COLLECTION",
    }
    response = await client.post("/api/v1/procedures/", json=payload)
    assert response.status_code == 201, f"Procedure creation failed: {response.text}"
    return response.json()["id"]


async def create_observed_property(client) -> str:
    payload = {
        "name": "Temperature",
        "domain": "ENVIRONMENTAL_BASICS",
        "value_type": "FLOAT",
    }
    response = await client.post("/api/v1/observed-properties/", json=payload)
    assert response.status_code == 201, f"Observed property creation failed: {response.text}"
    return response.json()["id"]


async def create_feature_of_interest(client) -> str:
    payload = {
        "name": "Test Feature",
        "feature_type": "ENVIRONMENT",
    }
    response = await client.post("/api/v1/features-of-interest/", json=payload)
    assert response.status_code == 201, f"Feature of interest creation failed: {response.text}"
    return response.json()["id"]


def datastream_payload(system_id: str, **overrides) -> dict:
    """Return a valid datastream payload with optional field overrides."""
    base = {
        "name": "Test Datastream",
        "description": "A test datastream",
        "system_id": system_id,
        "is_gps_enabled": False,
        "observation_result_type": "FLOAT",
        "properties": {"unit": "°C"},
    }
    base.update(overrides)
    return base


# ── creation ──────────────────────────────────────────────────────────────────

async def test_create_datastream_minimal(client):
    """Only required fields — no optional FKs."""
    system_id = await create_system(client)
    response = await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Datastream"
    assert data["system_id"] == system_id
    assert data["observation_result_type"] == "FLOAT"
    assert data["is_gps_enabled"] is False
    assert data["observed_property_id"] is None
    assert data["deployment_id"] is None
    assert data["procedure_id"] is None
    assert data["feature_of_interest_id"] is None


async def test_create_datastream_all_fks(client):
    """Datastream with all optional FK fields populated."""
    system_id = await create_system(client)
    deployment_id = await create_deployment(client, system_id)
    procedure_id = await create_procedure(client)
    observed_property_id = await create_observed_property(client)
    feature_of_interest_id = await create_feature_of_interest(client)

    payload = datastream_payload(
        system_id,
        deployment_id=deployment_id,
        procedure_id=procedure_id,
        observed_property_id=observed_property_id,
        feature_of_interest_id=feature_of_interest_id,
    )
    response = await client.post("/api/v1/datastreams/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["deployment_id"] == deployment_id
    assert data["procedure_id"] == procedure_id
    assert data["observed_property_id"] == observed_property_id
    assert data["feature_of_interest_id"] == feature_of_interest_id


async def test_create_datastream_missing_system_id(client):
    payload = {
        "name": "No System Datastream",
        "is_gps_enabled": False,
        "observation_result_type": "FLOAT",
    }
    response = await client.post("/api/v1/datastreams/", json=payload)
    assert response.status_code == 422


async def test_create_datastream_missing_name(client):
    system_id = await create_system(client)
    payload = datastream_payload(system_id)
    payload.pop("name")
    response = await client.post("/api/v1/datastreams/", json=payload)
    assert response.status_code == 422


async def test_create_datastream_missing_observation_result_type(client):
    system_id = await create_system(client)
    payload = datastream_payload(system_id)
    payload.pop("observation_result_type")
    response = await client.post("/api/v1/datastreams/", json=payload)
    assert response.status_code == 422


async def test_create_datastream_invalid_observation_result_type(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, observation_result_type="INVALID"),
    )
    assert response.status_code == 422


async def test_create_datastream_nonexistent_system_id(client):
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(str(uuid4())),
    )
    assert response.status_code == 400


async def test_create_datastream_nonexistent_deployment_id(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, deployment_id=str(uuid4())),
    )
    assert response.status_code in (400, 404)  # FK violation


async def test_create_datastream_nonexistent_procedure_id(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, procedure_id=str(uuid4())),
    )
    assert response.status_code in (400, 404)


async def test_create_datastream_nonexistent_observed_property_id(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, observed_property_id=str(uuid4())),
    )
    assert response.status_code in (400, 404)


async def test_create_datastream_nonexistent_feature_of_interest_id(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, feature_of_interest_id=str(uuid4())),
    )
    assert response.status_code in (400, 404)


async def test_create_datastream_all_result_types(client):
    system_id = await create_system(client)
    for vtype in ["BOOLEAN", "INTEGER", "FLOAT", "STRING", "JSON"]:
        response = await client.post(
            "/api/v1/datastreams/",
            json=datastream_payload(system_id, name=f"Datastream {vtype}", observation_result_type=vtype),
        )
        assert response.status_code == 201, f"Failed for result type {vtype}: {response.text}"


async def test_create_datastream_gps_enabled(client):
    system_id = await create_system(client)
    response = await client.post(
        "/api/v1/datastreams/",
        json=datastream_payload(system_id, is_gps_enabled=True),
    )
    assert response.status_code == 201
    assert response.json()["is_gps_enabled"] is True


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_datastream(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    response = await client.get(f"/api/v1/datastreams/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_datastream_data_integrity(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()
    fetched = (await client.get(f"/api/v1/datastreams/{created['id']}")).json()

    assert fetched["name"] == "Test Datastream"
    assert fetched["system_id"] == system_id
    assert fetched["observation_result_type"] == "FLOAT"
    assert fetched["properties"] == {"unit": "°C"}


async def test_get_nonexistent_datastream(client):
    response = await client.get(f"/api/v1/datastreams/{uuid4()}")
    assert response.status_code == 404


async def test_get_datastream_invalid_uuid(client):
    response = await client.get("/api/v1/datastreams/not-a-uuid")
    assert response.status_code == 422


async def test_list_datastreams(client):
    system_id = await create_system(client)
    await client.post("/api/v1/datastreams/", json=datastream_payload(system_id, name="DS 1"))
    await client.post("/api/v1/datastreams/", json=datastream_payload(system_id, name="DS 2"))

    response = await client.get("/api/v1/datastreams/")
    assert response.status_code == 200
    assert len(response.json()) >= 2


async def test_list_datastreams_pagination(client):
    system_id = await create_system(client)
    for i in range(5):
        await client.post("/api/v1/datastreams/", json=datastream_payload(system_id, name=f"Paginated DS {i}"))

    page1 = (await client.get("/api/v1/datastreams/?limit=2&offset=0")).json()
    page2 = (await client.get("/api/v1/datastreams/?limit=2&offset=2")).json()

    assert len(page1) == 2
    assert len(page2) == 2
    assert {d["id"] for d in page1}.isdisjoint({d["id"] for d in page2})


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_datastream_name(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    response = await client.put(
        f"/api/v1/datastreams/{created['id']}",
        json={"name": "Updated Datastream"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Datastream"


async def test_partial_update_datastream(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    response = await client.put(
        f"/api/v1/datastreams/{created['id']}",
        json={"description": "Updated description", "is_gps_enabled": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["is_gps_enabled"] is True
    assert data["name"] == "Test Datastream"  # unchanged


async def test_update_datastream_link_observed_property(client):
    """Link an observed property after creation."""
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()
    observed_property_id = await create_observed_property(client)

    response = await client.put(
        f"/api/v1/datastreams/{created['id']}",
        json={"observed_property_id": observed_property_id},
    )
    assert response.status_code == 200
    assert response.json()["observed_property_id"] == observed_property_id


async def test_update_datastream_invalid_result_type(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    response = await client.put(
        f"/api/v1/datastreams/{created['id']}",
        json={"observation_result_type": "INVALID"},
    )
    assert response.status_code == 422


async def test_update_nonexistent_datastream(client):
    response = await client.put(
        f"/api/v1/datastreams/{uuid4()}",
        json={"name": "Ghost Update"},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_datastream(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    delete_response = await client.delete(f"/api/v1/datastreams/{created['id']}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/datastreams/{created['id']}")
    assert get_response.status_code == 404


async def test_delete_datastream_twice(client):
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()

    await client.delete(f"/api/v1/datastreams/{created['id']}")
    second_delete = await client.delete(f"/api/v1/datastreams/{created['id']}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_datastream(client):
    response = await client.delete(f"/api/v1/datastreams/{uuid4()}")
    assert response.status_code == 404


async def test_delete_system_cascades_to_datastream(client):
    """Deleting a system should cascade and delete its datastreams."""
    system_id = await create_system(client)
    created = (await client.post("/api/v1/datastreams/", json=datastream_payload(system_id))).json()
    datastream_id = created["id"]

    await client.delete(f"/api/v1/systems/{system_id}")

    get_response = await client.get(f"/api/v1/datastreams/{datastream_id}")
    assert get_response.status_code == 404


# ── concurrency ───────────────────────────────────────────────────────────────

async def test_create_datastreams_concurrently(client):
    system_id = await create_system(client)

    async def create(i):
        response = await client.post(
            "/api/v1/datastreams/",
            json=datastream_payload(system_id, name=f"Concurrent DS {i}"),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(5)])


async def test_multiple_datastreams_same_system(client):
    """A single system can have multiple datastreams."""
    system_id = await create_system(client)
    for i in range(3):
        response = await client.post(
            "/api/v1/datastreams/",
            json=datastream_payload(system_id, name=f"DS {i}"),
        )
        assert response.status_code == 201