import pytest
from uuid import uuid4
import asyncio

pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

def feature_payload(**overrides) -> dict:
    """Return a valid feature of interest payload with optional field overrides."""
    base = {
        "name": "Test Feature",
        "description": "A test feature of interest",
        "feature_type": "ENVIRONMENT",
        "reference": "https://en.wikipedia.org/wiki/Environment",
        "location": "Athens, Greece",
        "properties": {"key": "value"},
        "media_links": ["https://example.com/image1.jpg"],
    }
    base.update(overrides)
    return base


async def create_feature(client, **overrides) -> dict:
    """Create a feature of interest and return the response JSON."""
    response = await client.post("/api/v1/features-of-interest/", json=feature_payload(**overrides))
    assert response.status_code == 201, f"Feature creation failed: {response.text}"
    return response.json()


# ── creation ──────────────────────────────────────────────────────────────────

async def test_create_feature(client):
    response = await client.post("/api/v1/features-of-interest/", json=feature_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Feature"
    assert data["feature_type"] == "ENVIRONMENT"
    assert data["location"] == "Athens, Greece"
    assert data["media_links"] == ["https://example.com/image1.jpg"]


async def test_create_feature_minimal(client):
    """Only required fields — optional fields should be None or empty."""
    payload = {
        "name": "Minimal Feature",
        "feature_type": "ATMOSPHERE",
    }
    response = await client.post("/api/v1/features-of-interest/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Feature"
    assert data["description"] is None
    assert data["reference"] is None
    assert data["location"] is None
    assert data["properties"] is None


async def test_create_feature_missing_name(client):
    payload = feature_payload()
    payload.pop("name")
    response = await client.post("/api/v1/features-of-interest/", json=payload)
    assert response.status_code == 422


async def test_create_feature_missing_type(client):
    payload = feature_payload()
    payload.pop("feature_type")
    response = await client.post("/api/v1/features-of-interest/", json=payload)
    assert response.status_code == 422


async def test_create_feature_invalid_type(client):
    response = await client.post(
        "/api/v1/features-of-interest/",
        json=feature_payload(feature_type="INVALID_TYPE"),
    )
    assert response.status_code == 422


async def test_create_feature_all_types(client):
    """Every valid FeatureOfInterestType should be accepted."""
    valid_types = [
        "ENVIRONMENT", "ATMOSPHERE", "HYDROSPHERE", "LITHOSPHERE",
        "BIOSPHERE", "BUILT_ENVIRONMENT", "INDIVIDUAL",
        "POPULATION", "OBJECT", "EVENT", "CUSTOM",
    ]
    for ftype in valid_types:
        response = await client.post(
            "/api/v1/features-of-interest/",
            json=feature_payload(name=f"Feature {ftype}", feature_type=ftype),
        )
        assert response.status_code == 201, f"Failed for type {ftype}: {response.text}"


async def test_create_feature_multiple_media_links(client):
    links = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/doc.pdf",
    ]
    response = await client.post(
        "/api/v1/features-of-interest/",
        json=feature_payload(media_links=links),
    )
    assert response.status_code == 201
    assert response.json()["media_links"] == links


async def test_create_feature_empty_media_links(client):
    response = await client.post(
        "/api/v1/features-of-interest/",
        json=feature_payload(media_links=[]),
    )
    assert response.status_code == 201
    assert response.json()["media_links"] is None or response.json()["media_links"] == []


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_feature(client):
    created = await create_feature(client)
    feature_id = created["id"]

    response = await client.get(f"/api/v1/features-of-interest/{feature_id}")
    assert response.status_code == 200
    assert response.json()["id"] == feature_id


async def test_get_feature_data_integrity(client):
    """All fields should round-trip correctly."""
    created = await create_feature(client)
    fetched = (await client.get(f"/api/v1/features-of-interest/{created['id']}")).json()

    assert fetched["name"] == "Test Feature"
    assert fetched["feature_type"] == "ENVIRONMENT"
    assert fetched["reference"] == "https://en.wikipedia.org/wiki/Environment"
    assert fetched["location"] == "Athens, Greece"
    assert fetched["properties"] == {"key": "value"}
    assert fetched["media_links"] == ["https://example.com/image1.jpg"]


async def test_get_nonexistent_feature(client):
    response = await client.get(f"/api/v1/features-of-interest/{uuid4()}")
    assert response.status_code == 404


async def test_get_feature_invalid_uuid(client):
    response = await client.get("/api/v1/features-of-interest/not-a-uuid")
    assert response.status_code == 422


async def test_list_features(client):
    await create_feature(client, name="List Feature 1")
    await create_feature(client, name="List Feature 2")

    response = await client.get("/api/v1/features-of-interest/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


async def test_list_features_pagination(client):
    for i in range(5):
        await create_feature(client, name=f"Paginated Feature {i}")

    page1 = (await client.get("/api/v1/features-of-interest/?limit=2&offset=0")).json()
    page2 = (await client.get("/api/v1/features-of-interest/?limit=2&offset=2")).json()

    assert len(page1) == 2
    assert len(page2) == 2
    assert {f["id"] for f in page1}.isdisjoint({f["id"] for f in page2})


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_feature(client):
    created = await create_feature(client)
    feature_id = created["id"]

    response = await client.put(
        f"/api/v1/features-of-interest/{feature_id}",
        json={"name": "Updated Feature Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Feature Name"


async def test_partial_update_feature(client):
    created = await create_feature(client)
    feature_id = created["id"]

    response = await client.put(
        f"/api/v1/features-of-interest/{feature_id}",
        json={"description": "Only description updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Only description updated"
    assert data["name"] == "Test Feature"          # unchanged
    assert data["feature_type"] == "ENVIRONMENT"   # unchanged


async def test_update_feature_media_links(client):
    created = await create_feature(client)
    feature_id = created["id"]

    new_links = ["https://example.com/new1.jpg", "https://example.com/new2.jpg"]
    response = await client.put(
        f"/api/v1/features-of-interest/{feature_id}",
        json={"media_links": new_links},
    )
    assert response.status_code == 200
    assert response.json()["media_links"] == new_links


async def test_update_feature_clear_media_links(client):
    created = await create_feature(client)
    feature_id = created["id"]

    response = await client.put(
        f"/api/v1/features-of-interest/{feature_id}",
        json={"media_links": []},
    )
    assert response.status_code == 200
    assert response.json()["media_links"] is None or response.json()["media_links"] == []


async def test_update_feature_invalid_type(client):
    created = await create_feature(client)
    feature_id = created["id"]

    response = await client.put(
        f"/api/v1/features-of-interest/{feature_id}",
        json={"feature_type": "UNSUPPORTED_TYPE"},
    )
    assert response.status_code == 422


async def test_update_nonexistent_feature(client):
    response = await client.put(
        f"/api/v1/features-of-interest/{uuid4()}",
        json={"name": "Ghost Update"},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_feature(client):
    created = await create_feature(client)
    feature_id = created["id"]

    delete_response = await client.delete(f"/api/v1/features-of-interest/{feature_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/features-of-interest/{feature_id}")
    assert get_response.status_code == 404


async def test_delete_feature_twice(client):
    created = await create_feature(client)
    feature_id = created["id"]

    await client.delete(f"/api/v1/features-of-interest/{feature_id}")
    second_delete = await client.delete(f"/api/v1/features-of-interest/{feature_id}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_feature(client):
    response = await client.delete(f"/api/v1/features-of-interest/{uuid4()}")
    assert response.status_code == 404


# ── concurrency ───────────────────────────────────────────────────────────────

async def test_create_features_concurrently(client):
    async def create(i):
        response = await client.post(
            "/api/v1/features-of-interest/",
            json=feature_payload(name=f"Concurrent Feature {i}"),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(5)])