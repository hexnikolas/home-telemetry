import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

def observed_property_payload(**overrides) -> dict:
    """Return a valid observed property payload with optional field overrides."""
    base = {
        "name": "Temperature",
        "description": "Measurement of thermal energy",
        "domain": "ENVIRONMENTAL_BASICS",
        "property_definition": "ISO 80000-5",
        "unit_definition": "Degrees Celsius",
        "unit_symbol": "°C",
        "reference": "https://en.wikipedia.org/wiki/Celsius",
        "keywords": ["heat", "thermal", "temperature"],
        "value_type": "FLOAT",
    }
    base.update(overrides)
    return base


async def create_observed_property(client, **overrides) -> dict:
    """Create an observed property and return the response JSON."""
    response = await client.post("/api/v1/observed-properties/", json=observed_property_payload(**overrides))
    assert response.status_code == 201, f"Observed property creation failed: {response.text}"
    return response.json()


# ── creation ──────────────────────────────────────────────────────────────────

async def test_create_observed_property(client):
    response = await client.post("/api/v1/observed-properties/", json=observed_property_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Temperature"
    assert data["domain"] == "ENVIRONMENTAL_BASICS"
    assert data["value_type"] == "FLOAT"
    assert data["unit_symbol"] == "°C"
    assert data["keywords"] == ["heat", "thermal", "temperature"]


async def test_create_observed_property_minimal(client):
    """Only required fields."""
    payload = {
        "name": "Humidity",
        "domain": "ENVIRONMENTAL_BASICS",
        "value_type": "FLOAT",
    }
    response = await client.post("/api/v1/observed-properties/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Humidity"
    assert data["description"] is None
    assert data["unit_symbol"] is None
    assert data["reference"] is None
    assert data["keywords"] is None or data["keywords"] == []


async def test_create_observed_property_missing_name(client):
    payload = observed_property_payload()
    payload.pop("name")
    response = await client.post("/api/v1/observed-properties/", json=payload)
    assert response.status_code == 422


async def test_create_observed_property_missing_domain(client):
    payload = observed_property_payload()
    payload.pop("domain")
    response = await client.post("/api/v1/observed-properties/", json=payload)
    assert response.status_code == 422


async def test_create_observed_property_missing_value_type(client):
    payload = observed_property_payload()
    payload.pop("value_type")
    response = await client.post("/api/v1/observed-properties/", json=payload)
    assert response.status_code == 422


async def test_create_observed_property_invalid_domain(client):
    response = await client.post(
        "/api/v1/observed-properties/",
        json=observed_property_payload(domain="INVALID_DOMAIN"),
    )
    assert response.status_code == 422


async def test_create_observed_property_invalid_value_type(client):
    response = await client.post(
        "/api/v1/observed-properties/",
        json=observed_property_payload(value_type="INVALID_TYPE"),
    )
    assert response.status_code == 422


async def test_create_observed_property_all_domains(client):
    valid_domains = [
        "ENVIRONMENTAL_BASICS", "AIR_QUALITY", "WATER_QUALITY", "ELECTRICAL",
        "LIGHT_AND_RADIATION", "MOTION_AND_POSITION", "MECHANICAL", "BIOLOGICAL",
        "BUILT_ENVIRONMENT", "REMOTE_SENSING", "ENERGY_AND_HEAT",
        "HEALTH_AND_BIOMEDICAL", "SPECIAL_CASES",
    ]
    for domain in valid_domains:
        response = await client.post(
            "/api/v1/observed-properties/",
            json=observed_property_payload(name=f"Property {domain}", domain=domain),
        )
        assert response.status_code == 201, f"Failed for domain {domain}: {response.text}"


async def test_create_observed_property_all_value_types(client):
    valid_types = ["BOOLEAN", "INTEGER", "FLOAT", "STRING", "JSON"]
    for vtype in valid_types:
        response = await client.post(
            "/api/v1/observed-properties/",
            json=observed_property_payload(name=f"Property {vtype}", value_type=vtype),
        )
        assert response.status_code == 201, f"Failed for value_type {vtype}: {response.text}"


async def test_create_observed_property_with_keywords(client):
    keywords = ["temp", "heat", "thermal energy", "celsius"]
    response = await client.post(
        "/api/v1/observed-properties/",
        json=observed_property_payload(keywords=keywords),
    )
    assert response.status_code == 201
    assert response.json()["keywords"] == keywords


async def test_create_observed_property_empty_keywords(client):
    response = await client.post(
        "/api/v1/observed-properties/",
        json=observed_property_payload(keywords=[]),
    )
    assert response.status_code == 201
    assert response.json()["keywords"] == [] or response.json()["keywords"] is None


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_observed_property(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    response = await client.get(f"/api/v1/observed-properties/{property_id}")
    assert response.status_code == 200
    assert response.json()["id"] == property_id


async def test_get_observed_property_data_integrity(client):
    """All fields should round-trip correctly."""
    created = await create_observed_property(client)
    fetched = (await client.get(f"/api/v1/observed-properties/{created['id']}")).json()

    assert fetched["name"] == "Temperature"
    assert fetched["domain"] == "ENVIRONMENTAL_BASICS"
    assert fetched["value_type"] == "FLOAT"
    assert fetched["unit_symbol"] == "°C"
    assert fetched["unit_definition"] == "Degrees Celsius"
    assert fetched["property_definition"] == "ISO 80000-5"
    assert fetched["reference"] == "https://en.wikipedia.org/wiki/Celsius"
    assert fetched["keywords"] == ["heat", "thermal", "temperature"]


async def test_get_nonexistent_observed_property(client):
    response = await client.get(f"/api/v1/observed-properties/{uuid4()}")
    assert response.status_code == 404


async def test_get_observed_property_invalid_uuid(client):
    response = await client.get("/api/v1/observed-properties/not-a-uuid")
    assert response.status_code == 422


async def test_list_observed_properties(client):
    await create_observed_property(client, name="List Property 1")
    await create_observed_property(client, name="List Property 2")

    response = await client.get("/api/v1/observed-properties/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


async def test_list_observed_properties_pagination(client):
    for i in range(5):
        await create_observed_property(client, name=f"Paginated Property {i}")

    page1 = (await client.get("/api/v1/observed-properties/?limit=2&offset=0")).json()
    page2 = (await client.get("/api/v1/observed-properties/?limit=2&offset=2")).json()

    assert len(page1) == 2
    assert len(page2) == 2
    assert {p["id"] for p in page1}.isdisjoint({p["id"] for p in page2})


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_observed_property(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    response = await client.put(
        f"/api/v1/observed-properties/{property_id}",
        json={"name": "Updated Temperature"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Temperature"


async def test_partial_update_observed_property(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    response = await client.put(
        f"/api/v1/observed-properties/{property_id}",
        json={"unit_symbol": "°F", "unit_definition": "Degrees Fahrenheit"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["unit_symbol"] == "°F"
    assert data["unit_definition"] == "Degrees Fahrenheit"
    assert data["name"] == "Temperature"        # unchanged
    assert data["domain"] == "ENVIRONMENTAL_BASICS"  # unchanged


async def test_update_observed_property_keywords(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    new_keywords = ["new", "keywords", "list"]
    response = await client.put(
        f"/api/v1/observed-properties/{property_id}",
        json={"keywords": new_keywords},
    )
    assert response.status_code == 200
    assert response.json()["keywords"] == new_keywords


async def test_update_observed_property_invalid_domain(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    response = await client.put(
        f"/api/v1/observed-properties/{property_id}",
        json={"domain": "INVALID_DOMAIN"},
    )
    assert response.status_code == 422


async def test_update_observed_property_invalid_value_type(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    response = await client.put(
        f"/api/v1/observed-properties/{property_id}",
        json={"value_type": "INVALID_TYPE"},
    )
    assert response.status_code == 422


async def test_update_nonexistent_observed_property(client):
    response = await client.put(
        f"/api/v1/observed-properties/{uuid4()}",
        json={"name": "Ghost Update"},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_observed_property(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    delete_response = await client.delete(f"/api/v1/observed-properties/{property_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/observed-properties/{property_id}")
    assert get_response.status_code == 404


async def test_delete_observed_property_twice(client):
    created = await create_observed_property(client)
    property_id = created["id"]

    await client.delete(f"/api/v1/observed-properties/{property_id}")
    second_delete = await client.delete(f"/api/v1/observed-properties/{property_id}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_observed_property(client):
    response = await client.delete(f"/api/v1/observed-properties/{uuid4()}")
    assert response.status_code == 404


# ── concurrency ───────────────────────────────────────────────────────────────

async def test_create_observed_properties_concurrently(client):
    async def create(i):
        response = await client.post(
            "/api/v1/observed-properties/",
            json=observed_property_payload(name=f"Concurrent Property {i}"),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(5)])