import contextlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from grpc import aio as grpc_aio

from app.grpc_server import ObservationServiceServicer
from protos import observations_pb2, observations_pb2_grpc

pytestmark = pytest.mark.asyncio


class _DummyDbContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _db_factory():
    return _DummyDbContext()


async def _start_test_server() -> tuple[grpc_aio.Server, str]:
    server = grpc_aio.server()
    observations_pb2_grpc.add_ObservationServiceServicer_to_server(
        ObservationServiceServicer(_db_factory),
        server,
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    return server, f"127.0.0.1:{port}"


async def test_grpc_client_can_connect_and_stream_observations():
    server, address = await _start_test_server()

    fake_obs = [
        SimpleNamespace(
            id="obs-1",
            datastream_id="ds-1",
            result_time=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
            result_numeric=21.5,
            result_text=None,
            result_boolean=None,
            result_complex=None,
            parameters={"unit": "C"},
        ),
        SimpleNamespace(
            id="obs-2",
            datastream_id="ds-1",
            result_time=datetime(2026, 6, 20, 10, 30, tzinfo=timezone.utc),
            result_numeric=22.1,
            result_text="warm",
            result_boolean=False,
            result_complex='{"quality": "good"}',
            parameters={},
        ),
    ]

    try:
        with patch("app.grpc_server.get_all_observations", new=AsyncMock(return_value=fake_obs)):
            async with grpc_aio.insecure_channel(address) as channel:
                stub = observations_pb2_grpc.ObservationServiceStub(channel)
                request = observations_pb2.GetObservationsRequest(datastream_id="ds-1", limit=10)
                streamed = [obs async for obs in stub.GetObservations(request)]

        assert len(streamed) == 2
        assert streamed[0].id == "obs-1"
        assert streamed[0].result_numeric == 21.5
        assert dict(streamed[0].parameters) == {"unit": "C"}
        assert streamed[1].result_text == "warm"
    finally:
        await server.stop(0)
        with contextlib.suppress(Exception):
            await server.wait_for_termination(timeout=1)


async def test_grpc_limit_zero_defaults_to_1000():
    server, address = await _start_test_server()
    mocked_get_all = AsyncMock(return_value=[])

    try:
        with patch("app.grpc_server.get_all_observations", new=mocked_get_all):
            async with grpc_aio.insecure_channel(address) as channel:
                stub = observations_pb2_grpc.ObservationServiceStub(channel)
                request = observations_pb2.GetObservationsRequest(datastream_id="ds-1", limit=0)
                _ = [obs async for obs in stub.GetObservations(request)]

        _, kwargs = mocked_get_all.call_args
        assert kwargs["limit"] == 1000
    finally:
        await server.stop(0)
        with contextlib.suppress(Exception):
            await server.wait_for_termination(timeout=1)


async def test_grpc_invalid_time_filters_are_ignored():
    server, address = await _start_test_server()
    mocked_get_all = AsyncMock(return_value=[])

    try:
        with patch("app.grpc_server.get_all_observations", new=mocked_get_all):
            async with grpc_aio.insecure_channel(address) as channel:
                stub = observations_pb2_grpc.ObservationServiceStub(channel)
                request = observations_pb2.GetObservationsRequest(
                    datastream_id="ds-1",
                    time_start="not-a-date",
                    time_end="still-not-a-date",
                    limit=5,
                )
                _ = [obs async for obs in stub.GetObservations(request)]

        _, kwargs = mocked_get_all.call_args
        assert kwargs["time_start"] is None
        assert kwargs["time_end"] is None
    finally:
        await server.stop(0)
        with contextlib.suppress(Exception):
            await server.wait_for_termination(timeout=1)
