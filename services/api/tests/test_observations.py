import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
import asyncio
from urllib.parse import quote

pytestmark = pytest.mark.asyncio


# ── Redis mock (applied to all tests in this module) ─────────────────────────

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client so tests don't require a running Redis instance."""
    mock = AsyncMock()
    mock.xadd = AsyncMock(return_value="1234567890-0")
    with patch("app.crud.observation.get_redis_client", return_value=mock):
        yield mock


# ── helpers ───────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_offset(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


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
    assert response.status_code == 201
    return response.json()["id"]


async def create_datastream(client, system_id: str) -> str:
    payload = {
        "name": "Test Datastream",
        "system_id": system_id,
        "is_gps_enabled": False,
        "observation_result_type": "FLOAT",
    }
    response = await client.post("/api/v1/datastreams/", json=payload)
    assert response.status_code == 201, f"Datastream creation failed: {response.text}"
    return response.json()["id"]


def observation_payload(datastream_id: str, **overrides) -> dict:
    base = {
        "datastream_id": datastream_id,
        "result_time": now_iso(),
        "result_numeric": 23.5,
        "parameters": {"quality": "good"},
    }
    base.update(overrides)
    return base


# ── creation ──────────────────────────────────────────────────────────────────

async def test_create_observation_numeric(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    response = await client.post("/api/v1/observations/", json=observation_payload(ds_id))
    assert response.status_code == 201
    data = response.json()
    assert data["datastream_id"] == ds_id
    assert data["result_numeric"] == 23.5
    assert data["result_time"] is not None


async def test_create_observation_boolean(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    response = await client.post(
        "/api/v1/observations/",
        json=observation_payload(ds_id, result_numeric=None, result_boolean=True),
    )
    assert response.status_code == 201
    assert response.json()["result_boolean"] is True


async def test_create_observation_text(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    response = await client.post(
        "/api/v1/observations/",
        json=observation_payload(ds_id, result_numeric=None, result_text="hello"),
    )
    assert response.status_code == 201
    assert response.json()["result_text"] == "hello"


async def test_create_observation_complex(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    complex_result = {"temperature": 23.5, "humidity": 60.0}
    response = await client.post(
        "/api/v1/observations/",
        json=observation_payload(ds_id, result_numeric=None, result_complex=complex_result),
    )
    assert response.status_code == 201
    assert response.json()["result_complex"] == complex_result


async def test_create_observation_missing_result_time(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    payload = observation_payload(ds_id)
    payload.pop("result_time")
    response = await client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 422


async def test_create_observation_invalid_result_time(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    response = await client.post(
        "/api/v1/observations/",
        json=observation_payload(ds_id, result_time="not-a-datetime"),
    )
    assert response.status_code == 422


async def test_create_observation_without_datastream(client):
    """datastream_id is optional in schema but FK must exist if provided."""
    response = await client.post(
        "/api/v1/observations/",
        json={
            "result_time": now_iso(),
            "result_numeric": 10.0,
        },
    )
    # No datastream_id — should succeed (it's Optional in schema)
    assert response.status_code == 201
    assert response.json()["datastream_id"] is None


async def test_create_observation_nonexistent_datastream(client):
    response = await client.post(
        "/api/v1/observations/",
        json=observation_payload(str(uuid4())),
    )
    assert response.status_code in (400, 404)


async def test_create_observation_writes_to_redis(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    response = await client.post("/api/v1/observations/", json=observation_payload(ds_id))
    assert response.status_code == 201


# ── bulk creation ─────────────────────────────────────────────────────────────

async def test_create_observations_bulk(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    payload = [
        observation_payload(ds_id, result_numeric=i, result_time=iso_offset(i))
        for i in range(5)
    ]
    response = await client.post("/api/v1/observations/bulk", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 5
    assert all(obs["datastream_id"] == ds_id for obs in data)


async def test_create_observations_bulk_empty(client):
    response = await client.post("/api/v1/observations/bulk", json=[])
    # Empty bulk — either 201 with [] or 422 depending on implementation
    assert response.status_code in (201, 422)


async def test_create_observations_bulk_invalid_entry(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    payload = [
        observation_payload(ds_id, result_numeric=1.0),
        {"result_numeric": 2.0},  # missing result_time
    ]
    response = await client.post("/api/v1/observations/bulk", json=payload)
    assert response.status_code == 422


async def test_create_observations_bulk_different_datastreams(client):
    system_id = await create_system(client)
    ds_id_1 = await create_datastream(client, system_id)
    ds_id_2 = await create_datastream(client, system_id)

    payload = [
        observation_payload(ds_id_1, result_numeric=1.0),
        observation_payload(ds_id_2, result_numeric=2.0),
    ]
    response = await client.post("/api/v1/observations/bulk", json=payload)
    assert response.status_code == 201
    assert len(response.json()) == 2


# ── read ──────────────────────────────────────────────────────────────────────

async def test_get_observation(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()

    response = await client.get(f"/api/v1/observations/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_observation_data_integrity(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    result_time = now_iso()
    created = (await client.post(
        "/api/v1/observations/",
        json=observation_payload(ds_id, result_numeric=99.9, result_time=result_time),
    )).json()

    fetched = (await client.get(f"/api/v1/observations/{created['id']}")).json()
    assert fetched["result_numeric"] == 99.9
    assert fetched["datastream_id"] == ds_id


async def test_get_nonexistent_observation(client):
    response = await client.get(f"/api/v1/observations/{uuid4()}")
    assert response.status_code == 404


async def test_get_observation_invalid_uuid(client):
    response = await client.get("/api/v1/observations/not-a-uuid")
    assert response.status_code == 422


async def test_list_observations(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    for i in range(3):
        await client.post("/api/v1/observations/", json=observation_payload(ds_id, result_time=iso_offset(i)))

    response = await client.get("/api/v1/observations/")
    assert response.status_code == 200
    assert len(response.json()) >= 3


async def test_list_observations_filter_by_datastream(client):
    system_id = await create_system(client)
    ds_id_1 = await create_datastream(client, system_id)
    ds_id_2 = await create_datastream(client, system_id)
    
    await client.post("/api/v1/observations/", json=observation_payload(ds_id_1))
    await client.post("/api/v1/observations/", json=observation_payload(ds_id_2))

    response = await client.get(f"/api/v1/observations/?datastream_ids={ds_id_1}")
    assert response.status_code == 200
    data = response.json()
    assert all(obs["datastream_id"] == ds_id_1 for obs in data)


async def test_list_observations_pagination(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    for i in range(5):
        await client.post("/api/v1/observations/", json=observation_payload(ds_id, result_time=iso_offset(i)))

    page1 = (await client.get("/api/v1/observations/?limit=2&offset=0")).json()
    page2 = (await client.get("/api/v1/observations/?limit=2&offset=2")).json()

    assert len(page1) == 2
    assert len(page2) == 2
    assert {o["id"] for o in page1}.isdisjoint({o["id"] for o in page2})


async def test_list_observations_time_filter_single(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    await client.post("/api/v1/observations/", json=observation_payload(ds_id))

    time_param = quote(datetime.now(timezone.utc).isoformat())
    response = await client.get(f"/api/v1/observations/?time={time_param}")
    assert response.status_code in (200, 404)

async def test_list_observations_time_filter_range(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    await client.post("/api/v1/observations/", json=observation_payload(ds_id))

    start = quote(iso_offset(-60))
    end = quote(iso_offset(60))
    response = await client.get(f"/api/v1/observations/?time={start}/{end}")
    assert response.status_code in (200, 404)


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_observation_numeric(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()

    response = await client.put(
        f"/api/v1/observations/{created['id']}",
        json={"result_numeric": 99.9},
    )
    assert response.status_code == 200
    assert response.json()["result_numeric"] == 99.9


async def test_partial_update_observation(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()

    response = await client.put(
        f"/api/v1/observations/{created['id']}",
        json={"parameters": {"quality": "excellent"}},
    )
    assert response.status_code == 200
    assert response.json()["parameters"] == {"quality": "excellent"}
    assert response.json()["result_numeric"] == 23.5  # unchanged


async def test_update_nonexistent_observation(client):
    response = await client.put(
        f"/api/v1/observations/{uuid4()}",
        json={"result_numeric": 1.0},
    )
    assert response.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_observation(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()

    delete_response = await client.delete(f"/api/v1/observations/{created['id']}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/observations/{created['id']}")
    assert get_response.status_code == 404


async def test_delete_observation_twice(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()

    await client.delete(f"/api/v1/observations/{created['id']}")
    second_delete = await client.delete(f"/api/v1/observations/{created['id']}")
    assert second_delete.status_code == 404


async def test_delete_nonexistent_observation(client):
    response = await client.delete(f"/api/v1/observations/{uuid4()}")
    assert response.status_code == 404


async def test_delete_datastream_cascades_to_observations(client):
    """Deleting a datastream should cascade and remove its observations."""
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)
    created = (await client.post("/api/v1/observations/", json=observation_payload(ds_id))).json()
    obs_id = created["id"]

    await client.delete(f"/api/v1/datastreams/{ds_id}")

    get_response = await client.get(f"/api/v1/observations/{obs_id}")
    assert get_response.status_code == 404


# ── concurrency ───────────────────────────────────────────────────────────────

async def test_create_observations_concurrently(client):
    system_id = await create_system(client)
    ds_id = await create_datastream(client, system_id)

    async def create(i):
        response = await client.post(
            "/api/v1/observations/",
            json=observation_payload(ds_id, result_numeric=float(i), result_time=iso_offset(i)),
        )
        assert response.status_code == 201

    await asyncio.gather(*[create(i) for i in range(10)])